"""
Multi-Stop Route Optimization Service
Solves Traveling Salesman Problem for delivery and multi-destination routing
"""

import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import numpy as np
import asyncio
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import json
import redis

logger = logging.getLogger(__name__)

class OptimizationObjective(Enum):
    MINIMIZE_DISTANCE = "minimize_distance"
    MINIMIZE_TIME = "minimize_time"
    MINIMIZE_COST = "minimize_cost"
    BALANCE_TIME_DISTANCE = "balance_time_distance"

class VehicleType(Enum):
    CAR = "car"
    TRUCK = "truck" 
    MOTORCYCLE = "motorcycle"
    BICYCLE = "bicycle"
    WALKING = "walking"

@dataclass
class TimeWindow:
    """Time window constraint for a stop"""
    earliest: datetime
    latest: datetime
    
    def duration_minutes(self) -> int:
        return int((self.latest - self.earliest).total_seconds() / 60)

@dataclass
class Stop:
    """A stop in the multi-stop route"""
    stop_id: str
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None
    
    # Service requirements
    service_duration_minutes: int = 10  # Time spent at location
    time_window: Optional[TimeWindow] = None
    priority: int = 1  # Higher = more important
    
    # Delivery constraints
    pickup_amount: float = 0.0  # Items to pick up
    delivery_amount: float = 0.0  # Items to deliver
    
    # Visit requirements
    must_visit: bool = True
    visited: bool = False

@dataclass
class Vehicle:
    """Vehicle configuration for route optimization"""
    vehicle_id: str
    vehicle_type: VehicleType
    capacity: float  # Total carrying capacity
    max_distance_km: Optional[float] = None
    max_duration_minutes: Optional[int] = None
    
    # Costs
    cost_per_km: float = 0.5
    cost_per_minute: float = 0.1
    fixed_cost: float = 0.0
    
    # Speed profiles
    avg_speed_city: float = 30.0  # km/h
    avg_speed_highway: float = 80.0  # km/h

@dataclass
class OptimizationConstraints:
    """Constraints for route optimization"""
    max_total_duration_minutes: Optional[int] = None
    max_total_distance_km: Optional[float] = None
    max_stops_per_route: Optional[int] = None
    must_return_to_start: bool = True
    allow_split_deliveries: bool = False
    respect_time_windows: bool = True

@dataclass
class OptimizedRoute:
    """Result of route optimization"""
    route_id: str
    vehicle: Vehicle
    stops: List[Stop]  # In optimized order
    total_distance_km: float
    total_duration_minutes: float
    total_cost: float
    objective_value: float
    
    # Detailed timeline
    departure_time: datetime
    arrival_times: List[datetime] = field(default_factory=list)
    service_times: List[Tuple[datetime, datetime]] = field(default_factory=list)
    
    # Optimization metadata
    optimization_time_seconds: float = 0.0
    algorithm_used: str = "ortools"
    constraints_violated: List[str] = field(default_factory=list)

class MultiStopOptimizer:
    """Multi-stop route optimization service using OR-Tools"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        # Cache for distance/time matrices
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            self.cache_enabled = True
            logger.info("Redis cache enabled for route optimization")
        except:
            logger.warning("Redis cache not available")
            self.cache_enabled = False
            self.redis_client = None
        
        # Pre-computed distance matrices
        self.distance_matrices = {}
        self.time_matrices = {}
        
        # Performance tracking
        self.optimization_stats = {
            'total_optimizations': 0,
            'total_stops_optimized': 0,
            'avg_optimization_time': 0.0,
            'cache_hit_rate': 0.0
        }
    
    async def optimize_route(
        self,
        stops: List[Stop],
        vehicles: List[Vehicle],
        start_location: Optional[Tuple[float, float]] = None,
        objective: OptimizationObjective = OptimizationObjective.MINIMIZE_TIME,
        constraints: OptimizationConstraints = OptimizationConstraints(),
        departure_time: Optional[datetime] = None
    ) -> List[OptimizedRoute]:
        """
        Optimize multi-stop routes using OR-Tools solver
        
        Args:
            stops: List of stops to visit
            vehicles: Available vehicles
            start_location: Starting location (depot)
            objective: Optimization objective
            constraints: Route constraints
            departure_time: When to start the route
            
        Returns:
            List of optimized routes (one per vehicle)
        """
        try:
            start_time = datetime.now()
            
            # Validate inputs
            if len(stops) < 2:
                raise ValueError("Need at least 2 stops for optimization")
            
            if not vehicles:
                raise ValueError("Need at least 1 vehicle")
            
            # Set default departure time
            if not departure_time:
                departure_time = datetime.now()
            
            # Add depot (start location) if specified
            if start_location:
                depot = Stop(
                    stop_id="depot",
                    latitude=start_location[0],
                    longitude=start_location[1],
                    name="Depot",
                    service_duration_minutes=0,
                    must_visit=True
                )
                all_stops = [depot] + stops
                depot_index = 0
            else:
                all_stops = stops
                depot_index = 0  # Use first stop as depot
            
            # Build distance and time matrices
            distance_matrix = await self._build_distance_matrix(all_stops)
            time_matrix = await self._build_time_matrix(all_stops, departure_time)
            
            # Configure OR-Tools routing model
            num_locations = len(all_stops)
            num_vehicles = len(vehicles)
            
            # Create routing index manager
            manager = pywrapcp.RoutingIndexManager(
                num_locations, 
                num_vehicles, 
                depot_index
            )
            
            # Create routing model
            routing = pywrapcp.RoutingModel(manager)
            
            # Add distance/time dimension
            if objective in [OptimizationObjective.MINIMIZE_DISTANCE, OptimizationObjective.MINIMIZE_COST]:
                dimension_name = "Distance"
                matrix = distance_matrix
                scaling_factor = 100  # Scale for integer arithmetic
            else:
                dimension_name = "Time" 
                matrix = time_matrix
                scaling_factor = 1
            
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(matrix[from_node][to_node] * scaling_factor)
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            
            # Set cost of travel
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            # Add capacity constraints
            if any(v.capacity for v in vehicles):
                await self._add_capacity_constraints(routing, manager, all_stops, vehicles)
            
            # Add time window constraints
            if constraints.respect_time_windows:
                await self._add_time_window_constraints(
                    routing, manager, all_stops, time_matrix, departure_time
                )
            
            # Add distance/time limits
            await self._add_vehicle_constraints(routing, manager, vehicles, constraints)
            
            # Set search parameters
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            
            # Choose strategy based on problem size
            if len(all_stops) <= 20:
                search_parameters.first_solution_strategy = (
                    routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC
                )
                search_parameters.local_search_metaheuristic = (
                    routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
                )
                search_parameters.time_limit.seconds = 30
            else:
                search_parameters.first_solution_strategy = (
                    routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
                )
                search_parameters.local_search_metaheuristic = (
                    routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC
                )
                search_parameters.time_limit.seconds = 60
            
            # Solve
            solution = routing.SolveWithParameters(search_parameters)
            
            if not solution:
                raise Exception("No solution found")
            
            # Extract optimized routes
            optimized_routes = await self._extract_routes(
                routing, manager, solution, all_stops, vehicles,
                distance_matrix, time_matrix, departure_time, objective
            )
            
            # Update performance stats
            optimization_time = (datetime.now() - start_time).total_seconds()
            await self._update_stats(len(stops), optimization_time)
            
            logger.info(f"Optimized {len(stops)} stops in {optimization_time:.2f}s")
            
            return optimized_routes
            
        except Exception as e:
            logger.error(f"Route optimization failed: {e}")
            # Return fallback simple routes
            return await self._create_fallback_routes(stops, vehicles, departure_time)
    
    async def _build_distance_matrix(self, stops: List[Stop]) -> List[List[float]]:
        """Build distance matrix between all stops"""
        num_stops = len(stops)
        matrix = [[0.0] * num_stops for _ in range(num_stops)]
        
        # Check cache for existing matrix
        cache_key = self._get_matrix_cache_key(stops, "distance")
        if self.cache_enabled:
            cached = self.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # Calculate distances
        for i in range(num_stops):
            for j in range(num_stops):
                if i != j:
                    distance = self._calculate_distance(
                        stops[i].latitude, stops[i].longitude,
                        stops[j].latitude, stops[j].longitude
                    )
                    matrix[i][j] = distance
        
        # Cache matrix
        if self.cache_enabled:
            self.redis_client.setex(
                cache_key,
                3600,  # 1 hour
                json.dumps(matrix)
            )
        
        return matrix
    
    async def _build_time_matrix(self, stops: List[Stop], departure_time: datetime) -> List[List[int]]:
        """Build time matrix between all stops (in minutes)"""
        num_stops = len(stops)
        matrix = [[0] * num_stops for _ in range(num_stops)]
        
        # For simplicity, estimate time from distance
        # In production, use real routing service with traffic data
        distance_matrix = await self._build_distance_matrix(stops)
        
        for i in range(num_stops):
            for j in range(num_stops):
                if i != j:
                    distance_km = distance_matrix[i][j]
                    # Assume average speed of 40 km/h in city
                    time_minutes = int((distance_km / 40.0) * 60)
                    # Add service time at destination
                    time_minutes += stops[j].service_duration_minutes
                    matrix[i][j] = time_minutes
        
        return matrix
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math
        
        R = 6371  # Earth radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    async def _add_capacity_constraints(
        self, 
        routing, 
        manager, 
        stops: List[Stop], 
        vehicles: List[Vehicle]
    ):
        """Add vehicle capacity constraints"""
        def demand_callback(from_index):
            from_node = manager.IndexToNode(from_index)
            return int(stops[from_node].delivery_amount)
        
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        
        # Add capacity dimension
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,  # null capacity slack
            [int(v.capacity) for v in vehicles],  # vehicle capacities
            True,  # start cumul to zero
            "Capacity"
        )
    
    async def _add_time_window_constraints(
        self,
        routing,
        manager,
        stops: List[Stop],
        time_matrix: List[List[int]],
        departure_time: datetime
    ):
        """Add time window constraints"""
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return time_matrix[from_node][to_node]
        
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        
        # Add time dimension
        max_time = 24 * 60  # 24 hours in minutes
        routing.AddDimension(
            time_callback_index,
            30,  # allow waiting time
            max_time,  # maximum time per vehicle
            False,  # don't force start cumul to zero
            "Time"
        )
        
        time_dimension = routing.GetDimensionOrDie("Time")
        
        # Add time window constraints for each stop
        for location_idx, stop in enumerate(stops):
            if stop.time_window:
                start_minutes = int(
                    (stop.time_window.earliest - departure_time).total_seconds() / 60
                )
                end_minutes = int(
                    (stop.time_window.latest - departure_time).total_seconds() / 60
                )
                
                index = manager.NodeToIndex(location_idx)
                time_dimension.CumulVar(index).SetRange(start_minutes, end_minutes)
    
    async def _add_vehicle_constraints(
        self,
        routing,
        manager,
        vehicles: List[Vehicle],
        constraints: OptimizationConstraints
    ):
        """Add vehicle-specific constraints"""
        # Global constraints
        if constraints.max_total_distance_km:
            # This would be implemented with custom constraints
            pass
        
        if constraints.max_total_duration_minutes:
            time_dimension = routing.GetDimensionOrDie("Time")
            for vehicle_id in range(len(vehicles)):
                start_index = routing.Start(vehicle_id)
                end_index = routing.End(vehicle_id)
                time_dimension.SetSpanCostCoefficientForVehicle(100, vehicle_id)
    
    async def _extract_routes(
        self,
        routing,
        manager,
        solution,
        stops: List[Stop],
        vehicles: List[Vehicle],
        distance_matrix: List[List[float]],
        time_matrix: List[List[int]],
        departure_time: datetime,
        objective: OptimizationObjective
    ) -> List[OptimizedRoute]:
        """Extract optimized routes from OR-Tools solution"""
        routes = []
        
        for vehicle_id in range(len(vehicles)):
            route_stops = []
            route_distance = 0.0
            route_time = 0
            
            index = routing.Start(vehicle_id)
            
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_stops.append(stops[node_index])
                
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                
                if not routing.IsEnd(index):
                    next_node = manager.IndexToNode(index)
                    route_distance += distance_matrix[node_index][next_node]
                    route_time += time_matrix[node_index][next_node]
            
            # Skip empty routes
            if len(route_stops) <= 1:  # Only depot
                continue
            
            # Calculate timeline
            arrival_times = []
            service_times = []
            current_time = departure_time
            
            for i, stop in enumerate(route_stops):
                arrival_times.append(current_time)
                
                service_start = current_time
                service_end = current_time + timedelta(minutes=stop.service_duration_minutes)
                service_times.append((service_start, service_end))
                
                # Move to next stop
                if i < len(route_stops) - 1:
                    travel_time = time_matrix[i][i + 1]
                    current_time = service_end + timedelta(minutes=travel_time)
            
            # Calculate cost
            vehicle = vehicles[vehicle_id]
            total_cost = (
                route_distance * vehicle.cost_per_km +
                route_time * vehicle.cost_per_minute +
                vehicle.fixed_cost
            )
            
            route = OptimizedRoute(
                route_id=f"route_{vehicle_id}_{int(departure_time.timestamp())}",
                vehicle=vehicle,
                stops=route_stops,
                total_distance_km=route_distance,
                total_duration_minutes=route_time,
                total_cost=total_cost,
                objective_value=solution.ObjectiveValue(),
                departure_time=departure_time,
                arrival_times=arrival_times,
                service_times=service_times
            )
            
            routes.append(route)
        
        return routes
    
    async def _create_fallback_routes(
        self,
        stops: List[Stop],
        vehicles: List[Vehicle],
        departure_time: datetime
    ) -> List[OptimizedRoute]:
        """Create simple fallback routes when optimization fails"""
        logger.warning("Using fallback route creation")
        
        # Simple greedy nearest-neighbor approach
        routes = []
        remaining_stops = stops.copy()
        
        for i, vehicle in enumerate(vehicles):
            if not remaining_stops:
                break
            
            route_stops = []
            current_location = remaining_stops[0] if remaining_stops else None
            
            # Start with first remaining stop
            if current_location:
                route_stops.append(current_location)
                remaining_stops.remove(current_location)
            
            # Greedy nearest neighbor
            while remaining_stops and len(route_stops) < (vehicle.capacity or 50):
                nearest_stop = min(
                    remaining_stops,
                    key=lambda s: self._calculate_distance(
                        current_location.latitude, current_location.longitude,
                        s.latitude, s.longitude
                    )
                )
                
                route_stops.append(nearest_stop)
                remaining_stops.remove(nearest_stop)
                current_location = nearest_stop
            
            # Calculate route metrics
            total_distance = 0.0
            total_time = 0
            
            for j in range(len(route_stops) - 1):
                distance = self._calculate_distance(
                    route_stops[j].latitude, route_stops[j].longitude,
                    route_stops[j + 1].latitude, route_stops[j + 1].longitude
                )
                total_distance += distance
                total_time += int((distance / 40.0) * 60)  # Assume 40 km/h
                total_time += route_stops[j + 1].service_duration_minutes
            
            route = OptimizedRoute(
                route_id=f"fallback_route_{i}",
                vehicle=vehicle,
                stops=route_stops,
                total_distance_km=total_distance,
                total_duration_minutes=total_time,
                total_cost=total_distance * vehicle.cost_per_km,
                objective_value=total_distance,
                departure_time=departure_time,
                algorithm_used="fallback_greedy"
            )
            
            routes.append(route)
        
        return routes
    
    def _get_matrix_cache_key(self, stops: List[Stop], matrix_type: str) -> str:
        """Generate cache key for distance/time matrix"""
        locations = [(s.latitude, s.longitude) for s in stops]
        locations_hash = hash(tuple(locations))
        return f"matrix:{matrix_type}:{locations_hash}"
    
    async def _update_stats(self, num_stops: int, optimization_time: float):
        """Update performance statistics"""
        stats = self.optimization_stats
        
        stats['total_optimizations'] += 1
        stats['total_stops_optimized'] += num_stops
        
        # Running average of optimization time
        n = stats['total_optimizations']
        stats['avg_optimization_time'] = (
            (stats['avg_optimization_time'] * (n - 1) + optimization_time) / n
        )
    
    async def optimize_delivery_routes(
        self,
        pickup_stops: List[Stop],
        delivery_stops: List[Stop],
        vehicles: List[Vehicle],
        depot_location: Tuple[float, float],
        departure_time: Optional[datetime] = None
    ) -> List[OptimizedRoute]:
        """
        Specialized optimization for pickup and delivery problems
        """
        # Combine pickup and delivery stops with precedence constraints
        all_stops = pickup_stops + delivery_stops
        
        # Mark pickup/delivery relationships
        for i, pickup in enumerate(pickup_stops):
            if i < len(delivery_stops):
                pickup.pickup_amount = delivery_stops[i].delivery_amount
        
        return await self.optimize_route(
            stops=all_stops,
            vehicles=vehicles,
            start_location=depot_location,
            objective=OptimizationObjective.MINIMIZE_TIME,
            constraints=OptimizationConstraints(
                respect_time_windows=True,
                must_return_to_start=True
            ),
            departure_time=departure_time
        )
    
    async def get_optimization_stats(self) -> Dict:
        """Get optimization performance statistics"""
        return {
            **self.optimization_stats,
            'cache_enabled': self.cache_enabled,
            'matrix_cache_size': len(self.distance_matrices)
        }
    
    async def clear_cache(self):
        """Clear optimization caches"""
        if self.cache_enabled and self.redis_client:
            # Clear matrix caches
            keys = self.redis_client.keys("matrix:*")
            if keys:
                self.redis_client.delete(*keys)
        
        self.distance_matrices.clear()
        self.time_matrices.clear()
        
        logger.info("Optimization cache cleared")
    
    async def close(self):
        """Cleanup optimizer service"""
        if self.redis_client:
            self.redis_client.close()
        logger.info("Multi-stop optimizer closed")