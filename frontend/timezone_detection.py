import streamlit as st
import streamlit.components.v1 as components
import pytz
from datetime import datetime

def detect_timezone():
    """Detect user timezone using JavaScript and return it to Streamlit."""
    # Create a component that will detect the timezone and communicate back to Streamlit
    components.html(
        """
        <script>
        // Function that gets the timezone
        function getTimezone() {
            try {
                return Intl.DateTimeFormat().resolvedOptions().timeZone;
            } catch (e) {
                return "";
            }
        }
        
        // Send the timezone to Streamlit
        window.addEventListener('load', function() {
            const timezone = getTimezone();
            
            // Use Streamlit's component communication
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: timezone
            }, "*");
        });
        </script>
        """,
        height=0,
        key="timezone_detector"
    )
    
    # Get the timezone value from session state
    detected_timezone = st.session_state.get("timezone_detector", "")
    
    # If detection failed, return empty string
    return detected_timezone if detected_timezone else ""

# Main function to manage timezone
def get_user_timezone():
    """Get user timezone with fallback options."""
    # Initialize timezone in session state if not present
    if "user_timezone" not in st.session_state:
        st.session_state.user_timezone = "UTC"
        
    # Try to detect timezone
    detected_tz = detect_timezone()
    
    # If we detected a timezone and it's different from what we have stored
    if detected_tz and detected_tz != st.session_state.user_timezone:
        st.session_state.user_timezone = detected_tz
    
    # Get list of all timezones for manual selection
    all_timezones = sorted(pytz.common_timezones)
    
    # Allow manual override with a dropdown
    # Use a small column to not take up the whole width
    with st.container():
        col1, col2 = st.columns([1, 3])
        with col1:
            st.session_state.user_timezone = st.selectbox(
                "Your timezone:",
                options=all_timezones,
                index=all_timezones.index(st.session_state.user_timezone) if st.session_state.user_timezone in all_timezones else 0,
                key="timezone_selector"
            )
    
    # Convert to pytz timezone object
    try:
        user_tz = pytz.timezone(st.session_state.user_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        user_tz = pytz.timezone("UTC")
        st.session_state.user_timezone = "UTC"
    
    return user_tz

# Function to convert UTC timestamp to user's local time
def convert_to_local_time(timestamp_str, user_tz):
    """Convert a UTC timestamp string to the user's local time."""
    try:
        # Handle different timestamp formats
        if "Z" in timestamp_str:
            dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        elif "+" in timestamp_str or "-" in timestamp_str and ":" in timestamp_str[-6:]:
            dt_obj = datetime.fromisoformat(timestamp_str)
        else:
            # Assume UTC if no timezone info
            dt_obj = datetime.fromisoformat(timestamp_str)
            dt_obj = dt_obj.replace(tzinfo=pytz.UTC)
            
        # Convert to user's timezone
        local_time = dt_obj.astimezone(user_tz)
        return local_time.strftime("%b %d, %Y - %I:%M %p")
    except Exception as e:
        # Return original if parsing fails
        return timestamp_str

# Example usage
if __name__ == "__main__":
    st.title("Timezone Detection Demo")
    
    # Get the user's timezone
    user_tz = get_user_timezone()
    
    # Show the detected/selected timezone
    st.write(f"Using timezone: {st.session_state.user_timezone}")
    
    # Show the current time in user's timezone
    current_time = datetime.now(pytz.UTC).astimezone(user_tz)
    st.write(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Example of converting a timestamp
    example_timestamp = "2023-05-15T14:30:00Z"
    st.write(f"Example timestamp: {example_timestamp}")
    st.write(f"Converted to your time: {convert_to_local_time(example_timestamp, user_tz)}")