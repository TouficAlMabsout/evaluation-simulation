import streamlit as st
import streamlit.components.v1 as components
import pytz
from datetime import datetime

def get_user_timezone():
    """Get user timezone with fallback options."""
    # Initialize timezone in session state if not present
    if "user_timezone" not in st.session_state:
        st.session_state.user_timezone = "UTC"
    
    # Try to detect timezone using a simple JavaScript component without a key parameter
    timezone_html = """
    <script>
    let timezone = "UTC";
    try {
        timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    } catch (e) {
        console.error("Couldn't detect timezone:", e);
    }
    document.getElementById('detected-timezone').innerText = timezone;
    </script>
    <p id="detected-timezone" style="display:none;"></p>
    """
    
    components.html(timezone_html, height=0)
    
    # Allow manual selection
    timezone_col1, timezone_col2 = st.columns([1, 3])
    
    with timezone_col1:
        # List of common timezones for dropdown
        all_timezones = sorted(pytz.common_timezones)
        
        # Find current value index
        try:
            current_index = all_timezones.index(st.session_state.user_timezone)
        except ValueError:
            current_index = all_timezones.index("UTC") if "UTC" in all_timezones else 0
        
        # Timezone selector
        st.session_state.user_timezone = st.selectbox(
            "Your timezone:", 
            all_timezones,
            index=current_index
        )
    
    # Convert the timezone name to a pytz timezone object
    try:
        user_tz = pytz.timezone(st.session_state.user_timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        user_tz = pytz.timezone("UTC")
        st.session_state.user_timezone = "UTC"
    
    return user_tz

def convert_to_local_time(timestamp_str, user_tz):
    """Convert a UTC timestamp string to the user's local time."""
    try:
        # Handle different timestamp formats
        if isinstance(timestamp_str, str):
            if "Z" in timestamp_str:
                dt_obj = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            elif "+" in timestamp_str or "-" in timestamp_str and ":" in timestamp_str[-6:]:
                dt_obj = datetime.fromisoformat(timestamp_str)
            else:
                # Assume UTC if no timezone info
                dt_obj = datetime.fromisoformat(timestamp_str)
                dt_obj = dt_obj.replace(tzinfo=pytz.UTC)
        else:
            # Not a string, try to use it directly
            dt_obj = timestamp_str
            if dt_obj.tzinfo is None:
                dt_obj = dt_obj.replace(tzinfo=pytz.UTC)
            
        # Convert to user's timezone
        local_time = dt_obj.astimezone(user_tz)
        return local_time.strftime("%b %d, %Y - %I:%M %p")
    except Exception as e:
        # Return original if parsing fails
        return timestamp_str