import requests

def configure_doorbell_notifications(auth_token):
    # Define the API endpoint
    endpoint = "https://api.doorbellservice.com/v1/notifications/configure"
    
    # Define the headers including authorization
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # Define the payload for the request
    payload = {
        "email_notifications": {
            "deliveries": True
        },
        "push_notifications": {
            "doorbell_ring": True
        }
    }
    
    try:
        # Make the POST request to configure the notifications
        response = requests.post(endpoint, headers=headers, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Notifications configured successfully.")
        else:
            print(f"Failed to configure notifications. Status code: {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        # Handle any errors that occur during the request
        print(f"An error occurred: {e}")

# Main function to execute the code
def main():
    auth_token = "<your-custom-token>"
    configure_doorbell_notifications(auth_token)

# Execute the main function
if __name__ == "__main__":
    main()