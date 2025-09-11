import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
import uvicorn
from influxdb_client import InfluxDBClient
import redis
import json
import hashlib
import sys
import os

sys.path.append('/app')
from shared.config import QueryServiceConfig
from shared.utils import setup_logging, HealthChecker
from shared.models import MetricPoint

app = FastAPI(title="Query Service", version="1.0.0")
logger = setup_logging("query-service", QueryServiceConfig.LOG_LEVEL)
health_checker = HealthChecker()

class QueryService:
    def __init__(self):
        self.config = QueryServiceConfig()
        self.influxdb_client = None
        self.redis_client = None
        self.query_api = None
        
    async def initialize(self):
        """Initialize connections to InfluxDB and Redis."""
        try:
            # Initialize InfluxDB client
            self.influxdb_client = InfluxDBClient(
                url=self.config.INFLUXDB_URL,
                token=self.config.INFLUXDB_TOKEN,
                org=self.config.INFLUXDB_ORG
            )
            self.query_api = self.influxdb_client.query_api()
            logger.info("Connected to InfluxDB")
            
            # Initialize Redis client for caching
            self.redis_client = redis.Redis(
                host=self.config.REDIS_HOST,
                port=self.config.REDIS_PORT,
                db=self.config.REDIS_DB,
                decode_responses=True
            )
            logger.info("Connected to Redis")
            
            # Register health checks
            health_checker.add_check("influxdb", self._check_influxdb_health)
            health_checker.add_check("redis", self._check_redis_health)
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    def _check_influxdb_health(self):
        """Check InfluxDB connection health."""
        if not self.influxdb_client:
            raise Exception("InfluxDB client not initialized")
        
        health = self.influxdb_client.health()
        return {"status": health.status, "message": health.message}
    
    def _check_redis_health(self):
        """Check Redis connection health."""
        if not self.redis_client:
            raise Exception("Redis client not initialized")
        
        self.redis_client.ping()
        return {"status": "connected"}
    
    def _generate_cache_key(self, query_params: Dict[str, Any]) -> str:
        """Generate cache key from query parameters."""
        query_string = json.dumps(query_params, sort_keys=True)
        return f"query:{hashlib.md5(query_string.encode()).hexdigest()}"
    
    async def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached query result."""
        try:
            cached_result = self.redis_client.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for key: {cache_key}")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        return None
    
    async def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache query result."""
        try:
            self.redis_client.setex(
                cache_key,
                self.config.CACHE_TTL,
                json.dumps(result, default=str)
            )
            logger.info(f"Cached result for key: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")
    
    def build_flux_query(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_name: Optional[str] = None,
        host: Optional[str] = None,
        env: Optional[str] = None
    ) -> str:
        """Build Flux query for InfluxDB."""
        
        # Base query
        query = f'''
        from(bucket: "{self.config.INFLUXDB_BUCKET}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
        '''
        
        # Add metric name filter
        if metric_name:
            query += f'  |> filter(fn: (r) => r._measurement == "{metric_name}")\n'
        
        # Add host filter
        if host:
            query += f'  |> filter(fn: (r) => r.host == "{host}")\n'
        
        # Add environment filter
        if env:
            query += f'  |> filter(fn: (r) => r.env == "{env}")\n'
        
        # Add field filter (we store values in "value" field)
        query += '  |> filter(fn: (r) => r._field == "value")\n'
        
        return query.strip()
    
    async def query_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        metric_name: Optional[str] = None,
        host: Optional[str] = None,
        env: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query metrics from InfluxDB."""
        
        # Check cache first
        query_params = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "metric_name": metric_name,
            "host": host,
            "env": env
        }
        cache_key = self._generate_cache_key(query_params)
        
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Build and execute query
            flux_query = self.build_flux_query(start_time, end_time, metric_name, host, env)
            logger.info(f"Executing query: {flux_query}")
            
            result = self.query_api.query(flux_query)
            
            # Process results
            data_points = []
            for table in result:
                for record in table.records:
                    data_points.append({
                        "timestamp": record.get_time().isoformat(),
                        "metric": record.get_measurement(),
                        "value": record.get_value(),
                        "labels": {
                            k: v for k, v in record.values.items()
                            if k not in ['_time', '_value', '_field', '_measurement', 'result', 'table']
                        }
                    })
            
            response = {
                "data": data_points,
                "count": len(data_points),
                "query_time": datetime.utcnow().isoformat()
            }
            
            # Cache the result
            await self._cache_result(cache_key, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_latest_metric(self, metric_name: str, host: Optional[str] = None) -> Dict[str, Any]:
        """Get the latest value for a specific metric."""
        
        # Query for the last hour to get latest value
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        try:
            # Build query for latest value
            query = f'''
            from(bucket: "{self.config.INFLUXDB_BUCKET}")
              |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
              |> filter(fn: (r) => r._measurement == "{metric_name}")
              |> filter(fn: (r) => r._field == "value")
            '''
            
            if host:
                query += f'  |> filter(fn: (r) => r.host == "{host}")\n'
            
            query += '  |> last()\n'
            
            result = self.query_api.query(query)
            
            for table in result:
                for record in table.records:
                    return {
                        "timestamp": record.get_time().isoformat(),
                        "metric": record.get_measurement(),
                        "value": record.get_value(),
                        "labels": {
                            k: v for k, v in record.values.items()
                            if k not in ['_time', '_value', '_field', '_measurement', 'result', 'table']
                        }
                    }
            
            return {"error": "No data found"}
            
        except Exception as e:
            logger.error(f"Latest metric query failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_metric_aggregation(
        self,
        metric_name: str,
        aggregation: str,
        window: str = "1h",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregated metric data."""
        
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()
        
        # Validate aggregation type
        valid_aggregations = ["mean", "sum", "count", "min", "max"]
        if aggregation not in valid_aggregations:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid aggregation. Must be one of: {valid_aggregations}"
            )
        
        try:
            query = f'''
            from(bucket: "{self.config.INFLUXDB_BUCKET}")
              |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
              |> filter(fn: (r) => r._measurement == "{metric_name}")
              |> filter(fn: (r) => r._field == "value")
              |> aggregateWindow(every: {window}, fn: {aggregation}, createEmpty: false)
            '''
            
            result = self.query_api.query(query)
            
            data_points = []
            for table in result:
                for record in table.records:
                    data_points.append({
                        "timestamp": record.get_time().isoformat(),
                        "metric": record.get_measurement(),
                        "value": record.get_value(),
                        "aggregation": aggregation,
                        "window": window
                    })
            
            return {
                "data": data_points,
                "count": len(data_points),
                "aggregation": aggregation,
                "window": window
            }
            
        except Exception as e:
            logger.error(f"Aggregation query failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Global query service instance
query_service = QueryService()

@app.on_event("startup")
async def startup_event():
    """Initialize the query service on startup."""
    await query_service.initialize()

@app.get("/query/metrics")
async def query_metrics(
    start: str = Query(..., description="Start time (ISO 8601)"),
    end: str = Query(..., description="End time (ISO 8601)"),
    metric: Optional[str] = Query(None, description="Metric name filter"),
    host: Optional[str] = Query(None, description="Host filter"),
    env: Optional[str] = Query(None, description="Environment filter")
):
    """Query metrics with time range and filters."""
    try:
        start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        return await query_service.query_metrics(
            start_time=start_time,
            end_time=end_time,
            metric_name=metric,
            host=host,
            env=env
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")

@app.get("/query/latest/{metric_name}")
async def get_latest_metric(
    metric_name: str,
    host: Optional[str] = Query(None, description="Host filter")
):
    """Get the latest value for a specific metric."""
    return await query_service.get_latest_metric(metric_name, host)

@app.get("/query/aggregate/{metric_name}")
async def get_metric_aggregation(
    metric_name: str,
    aggregation: str = Query(..., description="Aggregation type (mean, sum, count, min, max)"),
    window: str = Query("1h", description="Time window (e.g., 1h, 30m, 1d)"),
    start: Optional[str] = Query(None, description="Start time (ISO 8601)"),
    end: Optional[str] = Query(None, description="End time (ISO 8601)")
):
    """Get aggregated metric data."""
    start_time = None
    end_time = None
    
    if start:
        try:
            start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid start time format: {e}")
    
    if end:
        try:
            end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid end time format: {e}")
    
    return await query_service.get_metric_aggregation(
        metric_name=metric_name,
        aggregation=aggregation,
        window=window,
        start_time=start_time,
        end_time=end_time
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        health_status = await health_checker.run_checks()
        status_code = 200 if health_status["healthy"] else 503
        return JSONResponse(content=health_status, status_code=status_code)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            content={"healthy": False, "error": str(e)},
            status_code=503
        )

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "query-service",
        "version": "1.0.0",
        "endpoints": [
            "/query/metrics",
            "/query/latest/{metric_name}",
            "/query/aggregate/{metric_name}",
            "/health"
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=QueryServiceConfig.QUERY_SERVICE_PORT,
        log_level=QueryServiceConfig.LOG_LEVEL.lower()
    )