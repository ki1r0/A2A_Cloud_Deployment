from langchain_core.tools import tool
import httpx
from geopy.geocoders import Nominatim
import ssl
import certifi

USER_AGENT = "weather-agent"
http_client = httpx.Client(
    base_url="https://api.weather.gov",
    headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"},
    timeout=40.0,
    follow_redirects=True,
)
ctx = ssl.create_default_context(cafile=certifi.where())
geolocator = Nominatim(user_agent=USER_AGENT, ssl_context=ctx)


def format_forecast_period(period: dict) -> str:
    """Formats a single forecast period into a readable string."""
    return f"""
           {period.get('name', 'Unknown Period')}:
             Temperature: {period.get('temperature', 'N/A')}°{period.get('temperatureUnit', 'F')}
             Wind: {period.get('windSpeed', 'N/A')} {period.get('windDirection', 'N/A')}
             Short Forecast: {period.get('shortForecast', 'N/A')}
             Detailed Forecast: {period.get('detailedForecast', 'No detailed forecast provided.').strip()}
           """


@tool
def get_forecast(latitude: float, longitude: float) -> str:
    """Get the weather forecast for a specific location using latitude and longitude."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return "Invalid latitude or longitude provided."

    point_endpoint = f"/points/{latitude:.4f},{longitude:.4f}"
    try:
        points_response = http_client.get(point_endpoint)
        points_response.raise_for_status()
        points_data = points_response.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        return f"Unable to retrieve NWS gridpoint information: {e}"

    forecast_url = points_data.get("properties", {}).get("forecast")
    if not forecast_url:
        return "Could not find the NWS forecast endpoint."

    try:
        forecast_response = http_client.get(forecast_url)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        return f"Failed to retrieve detailed forecast data: {e}"

    periods = forecast_data.get("properties", {}).get("periods", [])
    if not periods:
        return "No forecast periods found for this location."

    forecasts = [format_forecast_period(period) for period in periods[:5]]
    return "\n---\n".join(forecasts)


@tool
def get_forecast_by_city(city: str, state: str) -> str:
    """Get the weather forecast for a specific US city and state."""
    try:
        location = geolocator.geocode(f"{city}, {state}, USA")
        if location is None:
            return f"Could not find coordinates for '{city}, {state}'."
    except Exception as e:
        return f"An error occurred during geocoding: {e}"

    return get_forecast(location.latitude, location.longitude)