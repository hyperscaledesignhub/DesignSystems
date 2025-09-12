"""
Navigation and Routing Service
Provides route planning, ETA calculation, and navigation instructions
"""

import logging
import heapq
import json
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import math
import asyncio
import redis

logger = logging.getLogger(__name__)

class TravelMode(Enum):
    DRIVING = "driving"
    WALKING = "walking"
    BICYCLING = "bicycling"
    TRANSIT = "transit"

@dataclass
class RouteNode:
    """Represents an intersection or point in the route graph"""
    node_id: str
    latitude: float
    longitude: float
    connections: List[str] = field(default_factory=list)
    
@dataclass
class RouteEdge:
    """Represents a road segment between two nodes"""
    edge_id: str
    from_node: str
    to_node: str
    distance_km: float
    base_duration_minutes: float
    road_type: str  # highway, arterial, local
    speed_limit_kmh: float
    
@dataclass
class RouteSegment:
    """A segment of the complete route"""
    start_location: Tuple[float, float]  # (lat, lon)
    end_location: Tuple[float, float]
    distance_km: float
    duration_minutes: float
    instruction: str
    road_name: str
    
@dataclass
class Route:
    """Complete route from origin to destination"""
    route_id: str
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    segments: List[RouteSegment]
    total_distance_km: float
    total_duration_minutes: float
    travel_mode: TravelMode
    waypoints: List[Tuple[float, float]]
    polyline: str  # Encoded polyline for map display
    traffic_adjusted: bool = False
    
@dataclass
class NavigationInstruction:
    """Turn-by-turn navigation instruction"""
    step_number: int
    instruction_text: str
    distance_meters: float
    duration_seconds: float
    maneuver: str  # turn-left, turn-right, continue, etc.
    location: Tuple[float, float]

class RoutingService:
    """
    Service for route planning and navigation
    Implements simplified A* algorithm for pathfinding
    """
    
    def __init__(self, graph_data_path: Optional[str] = None, 
                 cache_host: str = "localhost", cache_port: int = 6379):
        """Initialize routing service with graph data"""
        
        # Initialize route graph (simplified for demo)
        self.nodes: Dict[str, RouteNode] = {}
        self.edges: Dict[str, RouteEdge] = {}
        
        # Load graph data
        if graph_data_path:
            self._load_graph_data(graph_data_path)
        else:
            self._create_sample_graph()
        
        # Initialize cache for computed routes
        try:
            self.cache = redis.Redis(
                host=cache_host,
                port=cache_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.cache.ping()
            self.cache_enabled = True
            logger.info("Route cache connected")
        except:
            logger.warning("Route cache unavailable")
            self.cache_enabled = False
            self.cache = None
        
        # Travel mode configurations
        self.mode_speeds = {
            TravelMode.DRIVING: 60,  # km/h average
            TravelMode.WALKING: 5,   # km/h
            TravelMode.BICYCLING: 15,  # km/h
            TravelMode.TRANSIT: 40   # km/h average
        }
    
    def _create_sample_graph(self):
        """Create a sample road network graph for demonstration"""
        # Create sample nodes (intersections)
        sample_nodes = [
            RouteNode("node_1", 37.4419, -122.1430, ["node_2", "node_3"]),
            RouteNode("node_2", 37.4429, -122.1440, ["node_1", "node_4"]),
            RouteNode("node_3", 37.4409, -122.1420, ["node_1", "node_4", "node_5"]),
            RouteNode("node_4", 37.4439, -122.1450, ["node_2", "node_3", "node_6"]),
            RouteNode("node_5", 37.4399, -122.1410, ["node_3", "node_6"]),
            RouteNode("node_6", 37.4449, -122.1460, ["node_4", "node_5"])
        ]
        
        for node in sample_nodes:
            self.nodes[node.node_id] = node
        
        # Create sample edges (roads)
        sample_edges = [
            RouteEdge("edge_1", "node_1", "node_2", 0.15, 2, "local", 40),
            RouteEdge("edge_2", "node_1", "node_3", 0.12, 2, "local", 40),
            RouteEdge("edge_3", "node_2", "node_4", 0.18, 2.5, "arterial", 50),
            RouteEdge("edge_4", "node_3", "node_4", 0.25, 3, "arterial", 50),
            RouteEdge("edge_5", "node_3", "node_5", 0.13, 2, "local", 40),
            RouteEdge("edge_6", "node_4", "node_6", 0.20, 2.5, "highway", 80),
            RouteEdge("edge_7", "node_5", "node_6", 0.30, 4, "arterial", 50)
        ]
        
        for edge in sample_edges:
            self.edges[edge.edge_id] = edge
    
    def _load_graph_data(self, path: str):
        """Load road network graph from file"""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
                # Load nodes
                for node_data in data.get('nodes', []):
                    node = RouteNode(**node_data)
                    self.nodes[node.node_id] = node
                
                # Load edges
                for edge_data in data.get('edges', []):
                    edge = RouteEdge(**edge_data)
                    self.edges[edge.edge_id] = edge
                    
            logger.info(f"Loaded graph with {len(self.nodes)} nodes and {len(self.edges)} edges")
        except Exception as e:
            logger.error(f"Failed to load graph data: {e}")
            self._create_sample_graph()
    
    def _find_nearest_node(self, latitude: float, longitude: float) -> Optional[str]:
        """Find the nearest graph node to given coordinates"""
        min_distance = float('inf')
        nearest_node = None
        
        for node_id, node in self.nodes.items():
            distance = self._calculate_distance(
                latitude, longitude,
                node.latitude, node.longitude
            )
            if distance < min_distance:
                min_distance = distance
                nearest_node = node_id
        
        return nearest_node
    
    def _calculate_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        # Haversine formula
        R = 6371  # Earth radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _heuristic(self, node1: str, node2: str) -> float:
        """A* heuristic function - straight line distance"""
        n1 = self.nodes[node1]
        n2 = self.nodes[node2]
        return self._calculate_distance(
            n1.latitude, n1.longitude,
            n2.latitude, n2.longitude
        )
    
    async def find_route(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        travel_mode: TravelMode = TravelMode.DRIVING,
        waypoints: Optional[List[Tuple[float, float]]] = None,
        avoid_tolls: bool = False,
        avoid_highways: bool = False
    ) -> Optional[Route]:
        """
        Find optimal route between origin and destination
        
        Args:
            origin: (latitude, longitude) tuple
            destination: (latitude, longitude) tuple
            travel_mode: Mode of transportation
            waypoints: Optional intermediate points
            avoid_tolls: Avoid toll roads
            avoid_highways: Avoid highways
            
        Returns:
            Route object or None if no route found
        """
        try:
            # Find nearest nodes to origin and destination
            start_node = self._find_nearest_node(origin[0], origin[1])
            end_node = self._find_nearest_node(destination[0], destination[1])
            
            if not start_node or not end_node:
                logger.error("Could not find nodes near origin or destination")
                return None
            
            # Check cache for existing route
            cache_key = f"route:{start_node}:{end_node}:{travel_mode.value}"
            if self.cache_enabled:
                cached = self.cache.get(cache_key)
                if cached:
                    logger.info("Route cache hit")
                    return Route(**json.loads(cached))
            
            # Run A* algorithm
            path = await self._astar_search(
                start_node, end_node,
                avoid_highways=avoid_highways
            )
            
            if not path:
                logger.warning("No route found")
                return None
            
            # Build route from path
            route = await self._build_route(
                path, origin, destination, travel_mode
            )
            
            # Cache the route
            if self.cache_enabled and route:
                self.cache.setex(
                    cache_key,
                    3600,  # 1 hour TTL
                    json.dumps(route.__dict__)
                )
            
            return route
            
        except Exception as e:
            logger.error(f"Route finding error: {e}")
            return None
    
    async def _astar_search(
        self,
        start: str,
        goal: str,
        avoid_highways: bool = False
    ) -> Optional[List[str]]:
        """
        A* pathfinding algorithm
        
        Returns:
            List of node IDs representing the path, or None if no path exists
        """
        # Priority queue: (f_score, counter, node_id)
        counter = 0
        open_set = [(0, counter, start)]
        
        # Track visited nodes
        closed_set: Set[str] = set()
        
        # g_score: cost from start to node
        g_score = {start: 0}
        
        # Track path
        came_from = {}
        
        while open_set:
            _, _, current = heapq.heappop(open_set)
            
            if current == goal:
                # Reconstruct path
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start)
                return list(reversed(path))
            
            if current in closed_set:
                continue
                
            closed_set.add(current)
            
            # Check all neighbors
            current_node = self.nodes.get(current)
            if not current_node:
                continue
            
            for neighbor in current_node.connections:
                if neighbor in closed_set:
                    continue
                
                # Find edge between current and neighbor
                edge = None
                for e in self.edges.values():
                    if ((e.from_node == current and e.to_node == neighbor) or
                        (e.from_node == neighbor and e.to_node == current)):
                        edge = e
                        break
                
                if not edge:
                    continue
                
                # Skip highways if requested
                if avoid_highways and edge.road_type == "highway":
                    continue
                
                # Calculate tentative g_score
                tentative_g = g_score[current] + edge.distance_km
                
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    # This path is better
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    
                    # f_score = g_score + heuristic
                    f_score = tentative_g + self._heuristic(neighbor, goal)
                    
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbor))
        
        return None  # No path found
    
    async def _build_route(
        self,
        path: List[str],
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        travel_mode: TravelMode
    ) -> Route:
        """Build a Route object from a path of node IDs"""
        segments = []
        total_distance = 0
        total_duration = 0
        waypoints = []
        
        for i in range(len(path) - 1):
            from_node = self.nodes[path[i]]
            to_node = self.nodes[path[i + 1]]
            
            # Find edge
            edge = None
            for e in self.edges.values():
                if ((e.from_node == path[i] and e.to_node == path[i + 1]) or
                    (e.from_node == path[i + 1] and e.to_node == path[i])):
                    edge = e
                    break
            
            if not edge:
                continue
            
            # Calculate duration based on travel mode
            speed = self.mode_speeds[travel_mode]
            if travel_mode == TravelMode.DRIVING:
                speed = min(speed, edge.speed_limit_kmh)
            
            duration = (edge.distance_km / speed) * 60  # minutes
            
            # Create segment
            segment = RouteSegment(
                start_location=(from_node.latitude, from_node.longitude),
                end_location=(to_node.latitude, to_node.longitude),
                distance_km=edge.distance_km,
                duration_minutes=duration,
                instruction=self._generate_instruction(i, path, edge),
                road_name=f"Road_{edge.edge_id}"
            )
            
            segments.append(segment)
            total_distance += edge.distance_km
            total_duration += duration
            waypoints.append((from_node.latitude, from_node.longitude))
        
        # Add final waypoint
        if path:
            last_node = self.nodes[path[-1]]
            waypoints.append((last_node.latitude, last_node.longitude))
        
        # Generate route ID
        route_id = f"route_{datetime.now().timestamp()}"
        
        # Create polyline (simplified - just concatenate coordinates)
        polyline = self._encode_polyline(waypoints)
        
        return Route(
            route_id=route_id,
            origin=origin,
            destination=destination,
            segments=segments,
            total_distance_km=total_distance,
            total_duration_minutes=total_duration,
            travel_mode=travel_mode,
            waypoints=waypoints,
            polyline=polyline
        )
    
    def _generate_instruction(self, index: int, path: List[str], edge: RouteEdge) -> str:
        """Generate navigation instruction for a segment"""
        if index == 0:
            return f"Start on {edge.road_type} road"
        elif index == len(path) - 2:
            return "Arrive at destination"
        else:
            # Simplified turn detection
            return f"Continue on {edge.road_type} road for {edge.distance_km:.1f} km"
    
    def _encode_polyline(self, points: List[Tuple[float, float]]) -> str:
        """Encode waypoints as polyline (simplified version)"""
        # In production, use Google's polyline encoding algorithm
        encoded = []
        for lat, lon in points:
            encoded.append(f"{lat:.5f},{lon:.5f}")
        return "|".join(encoded)
    
    async def get_route_alternatives(
        self,
        origin: Tuple[float, float],
        destination: Tuple[float, float],
        travel_mode: TravelMode = TravelMode.DRIVING,
        max_alternatives: int = 3
    ) -> List[Route]:
        """
        Get multiple alternative routes
        
        Args:
            origin: Starting point
            destination: End point
            travel_mode: Mode of travel
            max_alternatives: Maximum number of alternatives
            
        Returns:
            List of alternative routes
        """
        routes = []
        
        # Find main route
        main_route = await self.find_route(origin, destination, travel_mode)
        if main_route:
            routes.append(main_route)
        
        # Find alternatives (simplified - just with different constraints)
        if len(routes) < max_alternatives:
            # Try avoiding highways
            alt_route = await self.find_route(
                origin, destination, travel_mode,
                avoid_highways=True
            )
            if alt_route and alt_route.route_id != main_route.route_id:
                routes.append(alt_route)
        
        return routes
    
    async def calculate_eta(
        self,
        route: Route,
        current_location: Optional[Tuple[float, float]] = None,
        traffic_factor: float = 1.0
    ) -> Dict[str, any]:
        """
        Calculate estimated time of arrival
        
        Args:
            route: The route to calculate ETA for
            current_location: Current location (if in progress)
            traffic_factor: Traffic multiplier (1.0 = normal, >1.0 = heavy traffic)
            
        Returns:
            Dictionary with ETA information
        """
        now = datetime.now()
        
        # Adjust duration for traffic
        adjusted_duration = route.total_duration_minutes * traffic_factor
        
        # If current location provided, calculate remaining time
        if current_location:
            # Find closest segment
            remaining_duration = adjusted_duration  # Simplified
            
            # In production, calculate actual remaining distance/time
            for i, segment in enumerate(route.segments):
                dist_to_segment = self._calculate_distance(
                    current_location[0], current_location[1],
                    segment.start_location[0], segment.start_location[1]
                )
                if dist_to_segment < 0.1:  # Within 100m
                    # Sum remaining segments
                    remaining_duration = sum(
                        s.duration_minutes for s in route.segments[i:]
                    ) * traffic_factor
                    break
        else:
            remaining_duration = adjusted_duration
        
        eta_time = now + timedelta(minutes=remaining_duration)
        
        return {
            'eta': eta_time.isoformat(),
            'duration_minutes': remaining_duration,
            'duration_text': self._format_duration(remaining_duration),
            'distance_km': route.total_distance_km,
            'distance_text': f"{route.total_distance_km:.1f} km",
            'traffic_conditions': self._get_traffic_condition(traffic_factor)
        }
    
    def _format_duration(self, minutes: float) -> str:
        """Format duration in human-readable form"""
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        
        if hours > 0:
            return f"{hours} hr {mins} min"
        else:
            return f"{mins} min"
    
    def _get_traffic_condition(self, factor: float) -> str:
        """Get traffic condition description"""
        if factor < 1.1:
            return "light"
        elif factor < 1.3:
            return "moderate"
        elif factor < 1.5:
            return "heavy"
        else:
            return "severe"
    
    async def get_turn_by_turn_instructions(
        self,
        route: Route
    ) -> List[NavigationInstruction]:
        """
        Generate turn-by-turn navigation instructions
        
        Args:
            route: The route to generate instructions for
            
        Returns:
            List of navigation instructions
        """
        instructions = []
        
        for i, segment in enumerate(route.segments):
            # Determine maneuver type
            if i == 0:
                maneuver = "start"
                text = f"Head out on {segment.road_name}"
            elif i == len(route.segments) - 1:
                maneuver = "arrive"
                text = "Arrive at your destination"
            else:
                # Simplified turn detection
                maneuver = "continue"
                text = f"Continue on {segment.road_name} for {segment.distance_km:.1f} km"
            
            instruction = NavigationInstruction(
                step_number=i + 1,
                instruction_text=text,
                distance_meters=segment.distance_km * 1000,
                duration_seconds=segment.duration_minutes * 60,
                maneuver=maneuver,
                location=segment.start_location
            )
            
            instructions.append(instruction)
        
        return instructions