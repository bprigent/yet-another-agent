"""Tool to get user location based on IP address."""

import requests
from tools.core.base_tool import ToolResult, log_tool_call, ensure_string_result
from langchain_core.tools import tool

@tool
@ensure_string_result
@log_tool_call("get_location_from_ip")
def get_location_from_ip(ip_address: str) -> ToolResult:
    """Get the geographic location information based on an IP address.
    
    Use this tool when you need to know the location of the user because their request is location sensitive. 
    
    Args:
        ip_address: Mandatory IP address to look up.
                   
    Returns:
        A formatted string with location information including city, region, country, 
        timezone, and coordinates.
    """
    try:
        url = f"http://ip-api.com/json/{ip_address}"
        response = requests.get(url, timeout=5)
        
        if response.status_code != 200:
            return ToolResult(
                success=False,
                error=f"Error: Could not retrieve location information. Status code: {response.status_code}"
            )
        
        data = response.json()
        
        # Check if the API returned an error
        if data.get("status") == "fail":
            error_message = data.get("message", "Unknown error")
            return ToolResult(
                success=False,
                error=f"Error retrieving location: {error_message}"
            )
        
        # Extract location information
        country = data.get("country", "Unknown")
        region = data.get("regionName", "Unknown")
        city = data.get("city", "Unknown")
        zip_code = data.get("zip", "Unknown")
        timezone = data.get("timezone", "Unknown")
        lat = data.get("lat")
        lon = data.get("lon")
        isp = data.get("isp", "Unknown")
        
        # Format the response
        location_info = [
            f"📍 Location Information (IP: {ip_address}):",
            f"  City: {city}",
            f"  Region: {region}",
            f"  Country: {country}",
            f"  ZIP Code: {zip_code}",
            f"  Timezone: {timezone}",
        ]
        
        if lat and lon:
            location_info.append(f"  Coordinates: {lat}, {lon}")
        
        location_info.append(f"  ISP: {isp}")
        
        return ToolResult(
            success=True,
            data="\n".join(location_info)
        )
    
    except requests.exceptions.Timeout:
        return ToolResult(
            success=False,
            error="Error: Request timed out while retrieving location information."
        )
    except requests.exceptions.RequestException as e:
        return ToolResult(
            success=False,
            error=f"Error: Could not retrieve location information. {str(e)}"
        )
    except Exception as e:
        return ToolResult(
            success=False,
            error=f"Error: An unexpected error occurred: {str(e)}"
        )

