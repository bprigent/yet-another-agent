"""Tool to get the user's public IP address."""

import requests


def get_user_ip() -> str:
    """Get the user's public IP address.
    
    Use this tool when you need to know the user's IP address. You may use this tool to use the answer for other tools (like get_location_from_ip).
    
    Returns:
        A string containing the user's public IP address, or an error message if retrieval fails.
    """
    try:
        # Use ipify.org to get public IP (free, no API key required)
        response = requests.get("https://api.ipify.org?format=json", timeout=5)
        
        if response.status_code == 200:
            ip_address = response.json().get("ip")
            if ip_address:
                return f"The user's IP address is: {ip_address}"
            else:
                return "Error: Could not retrieve IP address from response."
        else:
            return f"Error: Could not retrieve IP address. Status code: {response.status_code}"
    
    except requests.exceptions.Timeout:
        return "Error: Request timed out while retrieving IP address."
    except requests.exceptions.RequestException as e:
        return f"Error: Could not retrieve IP address. {str(e)}"
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"

