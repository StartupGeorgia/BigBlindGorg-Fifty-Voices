# Tools Implementation Guide

Based on research of Pipecat, LlamaIndex, and OpenAI Realtime API patterns.

## 🎯 Hybrid Approach (Recommended)

### Strategy 1: OpenAI Realtime Built-in Connectors (Quick Win)
### Strategy 2: Custom Pipecat Tools (Full Control)

---

## Strategy 1: OpenAI Realtime Built-in Connectors

### What OpenAI Provides Out-of-the-Box

The OpenAI Realtime API has **pre-built connectors** that handle OAuth and tool calling:

```python
# From openai-python SDK
connector_id options:
- connector_dropbox
- connector_gmail
- connector_googlecalendar
- connector_googledrive
- connector_microsoftteams
- connector_outlookcalendar
- connector_outlookemail
- connector_sharepoint
```

### Implementation

**Step 1: User Connects via OAuth (Frontend)**
```typescript
// User clicks "Connect Google Calendar"
// Redirect to OpenAI OAuth URL
window.location.href = `https://api.openai.com/v1/oauth/authorize?connector_id=connector_googlecalendar&client_id=${CLIENT_ID}&redirect_uri=${REDIRECT_URI}`;
```

**Step 2: Store Token (Backend)**
```python
# OAuth callback endpoint
@router.get("/integrations/openai/callback")
async def openai_oauth_callback(code: str, state: str):
    # Exchange code for token
    token_response = await exchange_openai_code(code)

    # Save to database
    await save_user_integration(
        user_id=get_user_from_state(state),
        integration_id="google-calendar",
        provider="openai",
        access_token=token_response["access_token"],
        connector_id="connector_googlecalendar"
    )
```

**Step 3: Use in Voice Agent (No Custom Code!)**
```python
# When creating Pipecat session
llm = OpenAIRealtimeLLMService(
    api_key=openai_key,
    model="gpt-realtime",
    tools=[
        {
            "type": "connector",
            "connector_id": "connector_googlecalendar",  # That's it!
        }
    ]
)
```

**Benefits:**
- ✅ No tool function code needed
- ✅ OAuth handled by OpenAI
- ✅ Production-ready
- ✅ Automatic updates when APIs change

**Limitations:**
- ❌ Only works with OpenAI Realtime
- ❌ Limited to 8 pre-built connectors
- ❌ No customization of tool behavior

---

## Strategy 2: Custom Pipecat Tools

Based on official Pipecat examples, here's the pattern:

### Pattern from Pipecat Examples

```python
# examples/foundational/20a-persistent-context-openai.py

# Step 1: Define tool schema
tools = [
    {
        "type": "function",
        "function": {
            "name": "check_calendar_availability",
            "description": "Check if user is available at a specific time",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in HH:MM format"
                    }
                },
                "required": ["date", "time"]
            }
        }
    }
]

# Step 2: Implement the function
async def check_calendar_availability(
    function_name: str,
    tool_call_id: str,
    arguments: dict,
    llm: LLMService,
    context: LLMContext,
    result_callback: callable
):
    """Check calendar availability - called by LLM during conversation"""
    date = arguments["date"]
    time = arguments["time"]

    # Get user's Google Calendar credentials from database
    user_id = context.get("user_id")
    credentials = await get_integration_credentials(user_id, "google-calendar")

    # Call Google Calendar API
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials

    creds = Credentials(
        token=credentials["access_token"],
        refresh_token=credentials["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET
    )

    service = build('calendar', 'v3', credentials=creds)

    # Check availability
    events_result = service.events().list(
        calendarId='primary',
        timeMin=f"{date}T{time}:00Z",
        timeMax=f"{date}T{time}:00Z",  # Same time for point check
        singleEvents=True
    ).execute()

    events = events_result.get('items', [])
    is_available = len(events) == 0

    # Return result to LLM
    result = {
        "available": is_available,
        "message": "Available" if is_available else f"Busy - {len(events)} conflicting events"
    }

    await result_callback(result)

# Step 3: Register function with LLM
llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"))
llm.register_function("check_calendar_availability", check_calendar_availability)

# Step 4: Pass tools to context
context = LLMContext(messages, tools)
```

### Complete Example: Google Calendar Tool

**File: `backend/app/services/tools/google_calendar.py`**

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Dict, Any
from app.db.session import AsyncSession
from app.models.integration import UserIntegration
from sqlalchemy import select

class GoogleCalendarTools:
    """Google Calendar tools for voice agents"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_credentials(self, user_id: int) -> Credentials:
        """Get user's Google Calendar credentials from database"""
        result = await self.db.execute(
            select(UserIntegration).where(
                UserIntegration.user_id == user_id,
                UserIntegration.integration_id == "google-calendar",
                UserIntegration.is_active == True
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            raise ValueError("Google Calendar not connected")

        return Credentials(
            token=integration.access_token,
            refresh_token=integration.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )

    async def check_availability(
        self,
        function_name: str,
        tool_call_id: str,
        arguments: Dict[str, Any],
        llm,
        context,
        result_callback
    ):
        """Check if user is available at specific time"""
        try:
            user_id = context.get("user_id")
            date = arguments["date"]
            time = arguments["time"]

            # Get credentials
            creds = await self._get_credentials(user_id)
            service = build('calendar', 'v3', credentials=creds)

            # Query calendar
            time_min = f"{date}T{time}:00Z"
            time_max = (datetime.fromisoformat(time_min) + timedelta(hours=1)).isoformat()

            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True
            ).execute()

            events = events_result.get('items', [])
            is_available = len(events) == 0

            result = {
                "available": is_available,
                "message": "Available" if is_available else f"Busy - {len(events)} events",
                "events": [e.get('summary') for e in events]
            }

            await result_callback(result)

        except Exception as e:
            await result_callback({"error": str(e)})

    async def schedule_meeting(
        self,
        function_name: str,
        tool_call_id: str,
        arguments: Dict[str, Any],
        llm,
        context,
        result_callback
    ):
        """Schedule a new meeting"""
        try:
            user_id = context.get("user_id")
            title = arguments["title"]
            date = arguments["date"]
            start_time = arguments["start_time"]
            duration_minutes = arguments.get("duration_minutes", 30)

            # Get credentials
            creds = await self._get_credentials(user_id)
            service = build('calendar', 'v3', credentials=creds)

            # Create event
            start_dt = f"{date}T{start_time}:00Z"
            end_dt = (datetime.fromisoformat(start_dt) + timedelta(minutes=duration_minutes)).isoformat()

            event = {
                'summary': title,
                'start': {'dateTime': start_dt, 'timeZone': 'UTC'},
                'end': {'dateTime': end_dt, 'timeZone': 'UTC'},
            }

            created = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            result = {
                "success": True,
                "event_id": created['id'],
                "link": created.get('htmlLink'),
                "message": f"Meeting '{title}' scheduled for {date} at {start_time}"
            }

            await result_callback(result)

        except Exception as e:
            await result_callback({"error": str(e)})
```

### Tool Schema Definitions

**File: `backend/app/services/tools/schemas.py`**

```python
GOOGLE_CALENDAR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_calendar_availability",
            "description": "Check if the user is available at a specific date and time",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format, e.g., 2025-11-22"
                    },
                    "time": {
                        "type": "string",
                        "description": "Time in HH:MM format (24-hour), e.g., 14:30"
                    }
                },
                "required": ["date", "time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_meeting",
            "description": "Schedule a new meeting on the user's calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title/subject of the meeting"
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format"
                    },
                    "start_time": {
                        "type": "string",
                        "description": "Start time in HH:MM format (24-hour)"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Duration in minutes (default: 30)"
                    }
                },
                "required": ["title", "date", "start_time"]
            }
        }
    }
]
```

### Registering Tools in Pipecat Session

**File: `backend/app/services/voice/session.py`**

```python
from pipecat.services.openai.llm import OpenAILLMService
from app.services.tools.google_calendar import GoogleCalendarTools
from app.services.tools.schemas import GOOGLE_CALENDAR_TOOLS

async def create_voice_agent_session(agent_config: dict, user_id: int, db: AsyncSession):
    """Create a Pipecat voice agent session with tools"""

    # Initialize LLM
    llm = OpenAILLMService(
        api_key=settings.OPENAI_API_KEY,
        model=agent_config.get("llm_model", "gpt-4o")
    )

    # Initialize tool providers
    calendar_tools = GoogleCalendarTools(db)

    # Get agent's enabled tools from database
    enabled_tools = agent_config.get("enabled_tools", [])

    # Collect tool schemas
    tools = []

    # Register Google Calendar if enabled
    if "google-calendar" in enabled_tools:
        tools.extend(GOOGLE_CALENDAR_TOOLS)
        llm.register_function("check_calendar_availability", calendar_tools.check_availability)
        llm.register_function("schedule_meeting", calendar_tools.schedule_meeting)

    # Create context with tools
    context = LLMContext(
        messages=[
            {"role": "system", "content": agent_config["system_prompt"]}
        ],
        tools=tools
    )

    # Build Pipecat pipeline
    pipeline = Pipeline([
        # ... STT, LLM, TTS services
    ])

    return pipeline
```

## 🏗️ Implementation Plan

### Phase 1: Foundation (This Week)

**Backend:**
1. ✅ Database models (user_integrations, agent_tools)
2. ✅ OAuth endpoints (/oauth/start, /oauth/callback)
3. ✅ Integration CRUD API

**Approach: Start with OpenAI Realtime Connectors**
- Implement OAuth flow for Google Calendar
- Use OpenAI's built-in `connector_googlecalendar`
- Get quick win for users

### Phase 2: Custom Tools (Next Week)

**Build Google Calendar custom implementation:**
- Tool class with `check_availability()` and `schedule_meeting()`
- Register with Pipecat `llm.register_function()`
- Works with GPT-4o, Claude, Gemini

### Phase 3: Expand (Following Weeks)

Add more integrations following the same pattern.

## 📝 Example: Complete Flow

### User Journey:

1. **User connects Google Calendar**:
   - Clicks "Connect" on integrations page
   - Redirects to Google OAuth
   - Callback saves tokens to `user_integrations` table

2. **User creates agent with Calendar tool**:
   - Enables "Google Calendar" in Tools tab
   - Saves to `agent_tools` table

3. **Voice call happens**:
   ```
   User: "Am I free tomorrow at 2pm?"

   Agent (internal):
   - LLM decides to call check_calendar_availability
   - Function executes with user's OAuth credentials
   - Returns: {"available": true}

   Agent: "Yes, you're free tomorrow at 2pm. Would you like me to schedule something?"
   ```

## 🔑 Key Patterns from Research

### From Pipecat Examples:
```python
# Simple registration (from examples/foundational/20a-persistent-context-openai.py)
llm.register_function("function_name", async_function)
```

### From LlamaIndex:
```python
# ToolSpec pattern for organizing tools
class GoogleCalendarToolSpec(BaseToolSpec):
    spec_functions = ["check_availability", "schedule_meeting", "cancel_meeting"]

    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool.from_defaults(fn=self.check_availability),
            FunctionTool.from_defaults(fn=self.schedule_meeting),
        ]
```

### From CAMEL AI:
```python
# Toolkit pattern with get_tools()
tools = [
    *CalendarToolkit().get_tools(),
    *CRMToolkit().get_tools(),
]
```

## 🎬 Next Steps

1. **Decide**: OpenAI Realtime connectors vs custom tools (or both)?
2. **Implement**: OAuth backend for Google Calendar
3. **Build**: First tool function (check_availability)
4. **Test**: End-to-end voice call with tool calling
5. **Expand**: Add more integrations

Which approach do you want to start with?

## 📚 Sources

- [Pipecat Function Calling Guide](https://docs.pipecat.ai/guides/fundamentals/function-calling)
- [Pipecat Example: Function Calling](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/14-function-calling.py)
- [Pipecat Example: Persistent Context with Functions](https://github.com/pipecat-ai/pipecat/blob/main/examples/foundational/20a-persistent-context-openai.py)
- [LlamaIndex GoogleCalendarToolSpec](https://github.com/run-llama/llama_index/blob/main/llama-index-integrations/tools/llama-index-tools-google/llama_index/tools/google/calendar/base.py)
- [OpenAI Realtime Connectors](https://github.com/openai/openai-python/blob/main/src/openai/types/realtime/realtime_tools_config_union_param.py)
- [CAMEL AI Toolkits](https://github.com/camel-ai/camel/blob/master/examples/workforce/eigent.py)
