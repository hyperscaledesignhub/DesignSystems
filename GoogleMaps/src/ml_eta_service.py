"""
ML-Enhanced ETA Service with Dynamic Predictions
Uses machine learning for accurate travel time estimation
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import joblib
import asyncio
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import json
import redis

logger = logging.getLogger(__name__)

@dataclass
class ETAFeatures:
    """Features for ETA prediction"""
    distance_km: float
    base_duration_minutes: float
    hour_of_day: int
    day_of_week: int
    month: int
    historical_avg_speed: float
    current_traffic_factor: float
    weather_condition: str
    road_type_highway_pct: float
    road_type_arterial_pct: float
    road_type_local_pct: float
    construction_zones: int
    active_incidents: int
    is_holiday: bool
    is_rush_hour: bool
    population_density: float
    event_impact_score: float

@dataclass
class ETAPrediction:
    """ETA prediction result"""
    route_id: str
    predicted_duration_minutes: float
    confidence_interval: Tuple[float, float]
    factors: Dict[str, float]
    last_updated: datetime
    model_version: str

class MLETAService:
    """Machine Learning Enhanced ETA Service"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
        self.model_metrics = {}
        
        # Initialize Redis for caching
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            self.cache_enabled = True
        except:
            logger.warning("Redis cache not available for ML ETA service")
            self.cache_enabled = False
        
        # Historical data storage
        self.historical_data = []
        self.training_data = pd.DataFrame()
        
        # Weather conditions mapping
        self.weather_factors = {
            'clear': 1.0,
            'cloudy': 1.05,
            'rain': 1.25,
            'heavy_rain': 1.4,
            'snow': 1.6,
            'heavy_snow': 2.0,
            'fog': 1.3,
            'ice': 1.8
        }
        
    async def initialize(self):
        """Initialize ML models and load training data"""
        try:
            # Load or create initial models
            await self._load_models()
            
            # Generate synthetic training data if no historical data
            if self.training_data.empty:
                await self._generate_synthetic_training_data()
            
            # Train initial models
            await self._train_models()
            
            logger.info("ML ETA service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize ML ETA service: {e}")
            # Fallback to simple linear model
            await self._initialize_fallback_model()
    
    async def _load_models(self):
        """Load pre-trained models from storage"""
        try:
            # In production, load from S3 or model registry
            # For demo, we'll train from scratch
            self.models = {
                'random_forest': RandomForestRegressor(
                    n_estimators=100,
                    max_depth=10,
                    random_state=42
                ),
                'gradient_boost': GradientBoostingRegressor(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                )
            }
            
            self.scalers = {
                'standard': StandardScaler()
            }
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    async def _generate_synthetic_training_data(self):
        """Generate synthetic training data for initial model"""
        np.random.seed(42)
        n_samples = 10000
        
        # Generate realistic features
        distances = np.random.exponential(10, n_samples)  # Most trips are short
        base_durations = distances * (60 / 50) + np.random.normal(0, 5, n_samples)  # ~50 km/h base
        
        hours = np.random.randint(0, 24, n_samples)
        days = np.random.randint(0, 7, n_samples)
        months = np.random.randint(1, 13, n_samples)
        
        # Rush hour effects
        is_rush = ((hours >= 7) & (hours <= 9)) | ((hours >= 17) & (hours <= 19))
        rush_multiplier = np.where(is_rush, np.random.uniform(1.3, 1.8, n_samples), 1.0)
        
        # Weather effects
        weather_conditions = np.random.choice(
            list(self.weather_factors.keys()),
            n_samples,
            p=[0.4, 0.2, 0.15, 0.05, 0.1, 0.02, 0.05, 0.03]
        )
        weather_multipliers = [self.weather_factors[w] for w in weather_conditions]
        
        # Traffic factors
        traffic_factors = np.random.lognormal(0, 0.3, n_samples)  # Usually around 1.0
        
        # Road type percentages
        highway_pct = np.random.beta(2, 5, n_samples)
        arterial_pct = np.random.beta(3, 3, n_samples) * (1 - highway_pct)
        local_pct = 1 - highway_pct - arterial_pct
        
        # Calculate actual duration with all factors
        actual_durations = (
            base_durations * 
            rush_multiplier * 
            np.array(weather_multipliers) * 
            traffic_factors *
            (1 + np.random.normal(0, 0.1, n_samples))  # Random noise
        )
        
        # Create DataFrame
        self.training_data = pd.DataFrame({
            'distance_km': distances,
            'base_duration_minutes': base_durations,
            'hour_of_day': hours,
            'day_of_week': days,
            'month': months,
            'historical_avg_speed': 50 + np.random.normal(0, 10, n_samples),
            'current_traffic_factor': traffic_factors,
            'weather_condition_encoded': [list(self.weather_factors.keys()).index(w) for w in weather_conditions],
            'road_type_highway_pct': highway_pct,
            'road_type_arterial_pct': arterial_pct,
            'road_type_local_pct': local_pct,
            'construction_zones': np.random.poisson(0.5, n_samples),
            'active_incidents': np.random.poisson(0.3, n_samples),
            'is_holiday': np.random.binomial(1, 0.05, n_samples),
            'is_rush_hour': is_rush.astype(int),
            'population_density': np.random.lognormal(8, 1, n_samples),
            'event_impact_score': np.random.gamma(1, 1, n_samples),
            'actual_duration_minutes': actual_durations
        })
        
        logger.info(f"Generated {len(self.training_data)} synthetic training samples")
    
    async def _train_models(self):
        """Train ML models on historical data"""
        try:
            if self.training_data.empty:
                logger.warning("No training data available")
                return
            
            # Prepare features
            feature_columns = [
                'distance_km', 'base_duration_minutes', 'hour_of_day',
                'day_of_week', 'month', 'historical_avg_speed',
                'current_traffic_factor', 'weather_condition_encoded',
                'road_type_highway_pct', 'road_type_arterial_pct',
                'road_type_local_pct', 'construction_zones',
                'active_incidents', 'is_holiday', 'is_rush_hour',
                'population_density', 'event_impact_score'
            ]
            
            X = self.training_data[feature_columns].fillna(0)
            y = self.training_data['actual_duration_minutes']
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scalers['standard'].fit_transform(X_train)
            X_test_scaled = self.scalers['standard'].transform(X_test)
            
            # Train models
            for name, model in self.models.items():
                logger.info(f"Training {name} model...")
                
                if name == 'random_forest':
                    model.fit(X_train, y_train)
                    y_pred = model.predict(X_test)
                    
                    # Feature importance
                    self.feature_importance[name] = dict(zip(
                        feature_columns,
                        model.feature_importances_
                    ))
                    
                else:  # gradient_boost
                    model.fit(X_train_scaled, y_train)
                    y_pred = model.predict(X_test_scaled)
                
                # Calculate metrics
                mae = mean_absolute_error(y_test, y_pred)
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                
                self.model_metrics[name] = {
                    'mae': mae,
                    'rmse': rmse,
                    'accuracy': 1 - (mae / y_test.mean())
                }
                
                logger.info(f"{name} - MAE: {mae:.2f}, RMSE: {rmse:.2f}, Accuracy: {self.model_metrics[name]['accuracy']:.3f}")
            
            # Save models (in production, save to S3/model registry)
            await self._save_models()
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
    
    async def _save_models(self):
        """Save trained models"""
        try:
            # In production, save to persistent storage
            model_info = {
                'version': '1.0',
                'trained_at': datetime.now().isoformat(),
                'metrics': self.model_metrics,
                'feature_importance': self.feature_importance
            }
            
            if self.cache_enabled:
                self.redis_client.set(
                    'ml_eta_model_info',
                    json.dumps(model_info),
                    ex=86400  # 24 hours
                )
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save models: {e}")
    
    async def predict_eta(
        self,
        route_id: str,
        features: ETAFeatures,
        ensemble: bool = True
    ) -> ETAPrediction:
        """Predict ETA using ML models"""
        try:
            # Check cache first
            cache_key = f"ml_eta:{route_id}:{hash(str(features))}"
            if self.cache_enabled:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return ETAPrediction(**json.loads(cached))
            
            # Prepare features for prediction
            feature_array = self._features_to_array(features)
            
            if ensemble:
                # Ensemble prediction
                predictions = []
                weights = []
                
                for name, model in self.models.items():
                    if name in self.model_metrics:
                        if name == 'random_forest':
                            pred = model.predict([feature_array])[0]
                        else:  # gradient_boost
                            feature_array_scaled = self.scalers['standard'].transform([feature_array])
                            pred = model.predict(feature_array_scaled)[0]
                        
                        predictions.append(pred)
                        # Weight by accuracy
                        weights.append(self.model_metrics[name]['accuracy'])
                
                if predictions:
                    # Weighted average
                    weights = np.array(weights) / sum(weights)
                    final_prediction = np.average(predictions, weights=weights)
                    
                    # Confidence interval based on model variance
                    std_dev = np.std(predictions)
                    confidence_lower = final_prediction - 1.96 * std_dev
                    confidence_upper = final_prediction + 1.96 * std_dev
                else:
                    # Fallback to base duration
                    final_prediction = features.base_duration_minutes
                    confidence_lower = final_prediction * 0.8
                    confidence_upper = final_prediction * 1.2
            else:
                # Use best performing model
                best_model = max(self.models.keys(), 
                               key=lambda x: self.model_metrics[x]['accuracy'])
                
                if best_model == 'random_forest':
                    final_prediction = self.models[best_model].predict([feature_array])[0]
                else:
                    feature_array_scaled = self.scalers['standard'].transform([feature_array])
                    final_prediction = self.models[best_model].predict(feature_array_scaled)[0]
                
                # Simple confidence interval
                confidence_lower = final_prediction * 0.9
                confidence_upper = final_prediction * 1.1
            
            # Create prediction result
            prediction = ETAPrediction(
                route_id=route_id,
                predicted_duration_minutes=max(final_prediction, 1.0),  # Minimum 1 minute
                confidence_interval=(confidence_lower, confidence_upper),
                factors=self._analyze_prediction_factors(features),
                last_updated=datetime.now(),
                model_version='1.0'
            )
            
            # Cache prediction
            if self.cache_enabled:
                self.redis_client.setex(
                    cache_key,
                    300,  # 5 minutes
                    json.dumps(prediction.__dict__, default=str)
                )
            
            return prediction
            
        except Exception as e:
            logger.error(f"ETA prediction failed: {e}")
            # Fallback to simple calculation
            return self._fallback_prediction(route_id, features)
    
    def _features_to_array(self, features: ETAFeatures) -> np.array:
        """Convert features to numpy array for prediction"""
        weather_encoded = list(self.weather_factors.keys()).index(
            features.weather_condition
        ) if features.weather_condition in self.weather_factors else 0
        
        return np.array([
            features.distance_km,
            features.base_duration_minutes,
            features.hour_of_day,
            features.day_of_week,
            features.month,
            features.historical_avg_speed,
            features.current_traffic_factor,
            weather_encoded,
            features.road_type_highway_pct,
            features.road_type_arterial_pct,
            features.road_type_local_pct,
            features.construction_zones,
            features.active_incidents,
            int(features.is_holiday),
            int(features.is_rush_hour),
            features.population_density,
            features.event_impact_score
        ])
    
    def _analyze_prediction_factors(self, features: ETAFeatures) -> Dict[str, float]:
        """Analyze which factors are contributing to the prediction"""
        factors = {}
        
        # Traffic impact
        if features.current_traffic_factor > 1.2:
            factors['heavy_traffic'] = (features.current_traffic_factor - 1.0) * 100
        
        # Weather impact
        weather_factor = self.weather_factors.get(features.weather_condition, 1.0)
        if weather_factor > 1.1:
            factors['weather'] = (weather_factor - 1.0) * 100
        
        # Rush hour impact
        if features.is_rush_hour:
            factors['rush_hour'] = 25  # ~25% impact
        
        # Construction impact
        if features.construction_zones > 0:
            factors['construction'] = features.construction_zones * 15
        
        # Incident impact
        if features.active_incidents > 0:
            factors['incidents'] = features.active_incidents * 20
        
        return factors
    
    def _fallback_prediction(self, route_id: str, features: ETAFeatures) -> ETAPrediction:
        """Fallback prediction when ML models fail"""
        duration = features.base_duration_minutes * features.current_traffic_factor
        
        # Apply weather factor
        weather_factor = self.weather_factors.get(features.weather_condition, 1.0)
        duration *= weather_factor
        
        # Apply rush hour factor
        if features.is_rush_hour:
            duration *= 1.25
        
        return ETAPrediction(
            route_id=route_id,
            predicted_duration_minutes=duration,
            confidence_interval=(duration * 0.8, duration * 1.2),
            factors={'fallback': True},
            last_updated=datetime.now(),
            model_version='fallback'
        )
    
    async def _initialize_fallback_model(self):
        """Initialize simple fallback model"""
        logger.info("Initializing fallback ETA model")
        self.models = {'fallback': None}
        self.model_metrics = {'fallback': {'accuracy': 0.7}}
    
    async def update_with_actual_journey(
        self,
        route_id: str,
        predicted_duration: float,
        actual_duration: float,
        features: ETAFeatures
    ):
        """Update models with actual journey data for continuous learning"""
        try:
            # Store for retraining
            actual_data = {
                'route_id': route_id,
                'predicted_duration': predicted_duration,
                'actual_duration': actual_duration,
                'features': features.__dict__,
                'error': actual_duration - predicted_duration,
                'timestamp': datetime.now().isoformat()
            }
            
            self.historical_data.append(actual_data)
            
            # Retrain periodically (every 1000 samples)
            if len(self.historical_data) % 1000 == 0:
                await self._incremental_training()
            
            logger.debug(f"Updated with actual journey data for route {route_id}")
            
        except Exception as e:
            logger.error(f"Failed to update with actual data: {e}")
    
    async def _incremental_training(self):
        """Perform incremental training with new data"""
        try:
            logger.info("Starting incremental model training...")
            
            # Convert historical data to DataFrame
            if self.historical_data:
                new_data = pd.DataFrame([
                    {**d['features'], 'actual_duration_minutes': d['actual_duration']}
                    for d in self.historical_data[-1000:]  # Last 1000 samples
                ])
                
                # Append to training data
                self.training_data = pd.concat([
                    self.training_data.tail(9000),  # Keep recent data
                    new_data
                ], ignore_index=True)
                
                # Retrain models
                await self._train_models()
                
                logger.info("Incremental training completed")
        
        except Exception as e:
            logger.error(f"Incremental training failed: {e}")
    
    def get_model_performance(self) -> Dict:
        """Get current model performance metrics"""
        return {
            'models': self.model_metrics,
            'feature_importance': self.feature_importance,
            'training_samples': len(self.training_data),
            'historical_samples': len(self.historical_data)
        }
    
    async def close(self):
        """Cleanup ML ETA service"""
        if self.cache_enabled:
            self.redis_client.close()
        logger.info("ML ETA service closed")