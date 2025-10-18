# agent.py
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
import os
import logging
from dotenv import load_dotenv

# Import tools set
try:
    from tools import tools
    # Direct tool functions for fallback
    from tools import (
        vehicle_search_tool,
        get_vehicle_details_tool,
        serper_search_tool,
    )
except Exception as e:
    tools = []
    print(f"Tools import failed: {e}")

load_dotenv()

# System prompt for Toyota AI Sales Agent
TOYOTA_SYSTEM_PROMPT = """
You are a friendly and knowledgeable Toyota AI Sales Assistant for Toyota Automobiles North America. Your role is to help customers explore Toyota vehicles, find inventory near their location, and schedule test drives.

**Your Personality:**
- Enthusiastic about Toyota vehicles and their features
- Professional yet conversational and approachable
- Knowledgeable about Toyota's complete lineup
- Proactive in suggesting next steps
- Honest and transparent about vehicle information

**Your Capabilities:**
- Search for Toyota vehicle information and specifications
- Find available inventory near customer ZIP codes
- Help schedule test drives at local dealerships
- Provide detailed vehicle comparisons and recommendations
- Remember customer preferences throughout the conversation

**Guidelines:**
1. **Toyota Focus Only:** Only discuss Toyota vehicles, features, and services
2. **Gather Information:** Ask for customer preferences (budget, needs, location) early in conversation
3. **Use Tools Wisely:** 
   - Use search_toyota_info for specifications, reviews, and features
   - Use search_inventory to find available vehicles near customers
   - Use get_vehicle_details for specific vehicle information
   - Use save_test_drive when customer wants to book an appointment
4. **Be Proactive:** Always suggest relevant next steps like viewing inventory or scheduling test drives
5. **Remember Context:** Keep track of customer preferences, location, and interests
6. **Accurate Information:** Only provide verified information from your tools
7. **Professional Communication:** Use proper formatting and clear explanations

**Conversation Flow:**
1. Greet warmly and ask how you can help
2. Gather customer needs (type of vehicle, budget, location, priorities)
3. Show relevant vehicles from inventory when possible
4. Provide detailed information using available tools
5. Proactively suggest test drives for interested customers
6. Help with scheduling and next steps

**Important Notes:**
- Always verify availability before suggesting vehicles
- Include dealership contact information when showing inventory
- Mention key Toyota features like Toyota Safety Sense, hybrid options, reliability
- Be enthusiastic about Toyota's innovation and quality
- If you don't have specific information, use the search tool or direct to official Toyota resources

Remember: Your goal is to help customers find their perfect Toyota vehicle and create a smooth path to ownership!
"""


def create_toyota_agent():
    """Create and configure the Toyota AI Sales Agent"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("toyota_agent")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # No API key: return None to allow tool-only fallback
        logging.warning("OPENAI_API_KEY missing; agent will use tool-only fallback.")
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Initialize OpenAI LLM
    llm = ChatOpenAI(
        model=model,
        temperature=0.7,
        openai_api_key=api_key,
        timeout=60,
        max_retries=2,
    )

    # Initialize conversation memory
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="output",
    )

    # Initialize agent with ReAct framework
   
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CONVERSATIONAL_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
        agent_kwargs={"system_message": TOYOTA_SYSTEM_PROMPT},
        handle_parsing_errors=True,
        max_iterations=5,
    )

    try:
        logger.info(f"Agent initialized with tools: {[t.name for t in tools]}")
    except Exception:
        pass

    return agent


def get_agent_response(agent, user_input, customer_context=None):
    """Get response from agent with optional customer context"""
    try:
        # Add customer context to input if provided
        if customer_context:
            context_parts = [
                f"- Name: {customer_context.get('name', 'Not provided')}",
                f"- Location (ZIP): {customer_context.get('zipcode', 'Not provided')}",
                f"- Email: {customer_context.get('email', 'Not provided')}",
                f"- Phone: {customer_context.get('phone', 'Not provided')}"
            ]
            
            # Add vehicle preferences if available
            if customer_context.get('preferred_type'):
                context_parts.append(f"- Preferred Vehicle Type: {customer_context.get('preferred_type')}")
            if customer_context.get('preferred_model'):
                context_parts.append(f"- Preferred Model: {customer_context.get('preferred_model')}")
            if customer_context.get('preferred_trim'):
                context_parts.append(f"- Preferred Trim: {customer_context.get('preferred_trim')}")
            
            context_info = (
                "Customer Context:\n" + "\n".join(context_parts) + "\n\n" +
                f"Customer Message: {user_input}"
            )

            # Prefer invoke; fallback to run for compatibility
            try:
                result = agent.invoke({"input": context_info})
                response = result.get("output", result) if isinstance(result, dict) else str(result)
            except Exception:
                response = agent.run(context_info)
        else:
            try:
                text = user_input or "Hello, I'm interested in Toyota vehicles."
                result = agent.invoke({"input": text})
                response = result.get("output", result) if isinstance(result, dict) else str(result)
            except Exception:
                response = agent.run(user_input)
            
        return response
        
    except Exception as e:
        error_response = f"""
I apologize, but I'm experiencing a technical issue. Here's how I can still help you:

🚗 **Toyota Vehicle Information:**
- Visit toyota.com for complete specifications
- Call 1-800-GO-TOYOTA for immediate assistance

📍 **Find Local Dealers:**
- Use toyota.com/dealers to find locations near you
- Get contact information and hours

📅 **Schedule Test Drives:**
- Contact your local Toyota dealer directly
- Many dealers offer online scheduling

I'm working to resolve this issue. Thank you for your patience!

Error details: {str(e)}
        """
        return error_response.strip()


class ToyotaAgentManager:
    """Manager class for Toyota AI Agent with session handling"""
    
    def __init__(self):
        self.agent = None
        self.customer_context = {}
        self._initialize_agent()
        self._logger = logging.getLogger("toyota_agent")
    
    def _initialize_agent(self):
        """Initialize the agent"""
        try:
            self.agent = create_toyota_agent()
        except Exception as e:
            print(f"❌ Failed to initialize agent: {e}")
            self.agent = None

    def _tool_fallback(self, user_input: str) -> str:
        """Minimal tool-only fallback when LLM is unavailable.
        - If zipcode is known (from context or message) optionally with model, show inventory.
        - Else try Serper for info-style queries.
        - Else prompt user for ZIP/model.
        """
        import re, json as _json
        zipcode = self.customer_context.get("zipcode")
        if not zipcode:
            m = re.search(r"\b(\d{5})\b", user_input)
            if m:
                zipcode = m.group(1)
        preferred_model = self.customer_context.get("preferred_model")

        # Inventory search path
        if zipcode:
            payload = {"zipcode": zipcode}
            if preferred_model:
                payload["model"] = preferred_model
            try:
                raw = vehicle_search_tool(_json.dumps(payload))
                data = _json.loads(raw)
                if data.get("ok") and data.get("results"):
                    lines = ["Here are some nearby Toyota vehicles:"]
                    for item in data["results"][:5]:
                        veh = item["vehicle"]; dlr = item["dealership"]
                        lines.append(
                            f"- {veh.get('model')} {veh.get('trim')} ({veh.get('color')}), ${veh.get('price'):,.0f} — {dlr.get('name')} {dlr.get('city')} {dlr.get('zipcode')}"
                        )
                    lines.append("You can click a vehicle card to schedule a test drive.")
                    return "\n".join(lines)
                else:
                    return "I couldn't find available inventory with the current filters. Try another model or ZIP."
            except Exception as e:
                return f"Inventory lookup failed: {e}"

        # Info search path via Serper (graceful fallback handled in tool)
        try:
            raw = serper_search_tool(_json.dumps({"q": user_input}))
            data = _json.loads(raw)
            text = data.get("text") or "I couldn't retrieve external info right now. Please try again later."
            return text
        except Exception:
            return "Please provide your ZIP code and preferred model to search local Toyota inventory."
    
    def set_customer_context(self, name=None, email=None, phone=None, zipcode=None, city=None, 
                           preferred_type=None, preferred_model=None, preferred_trim=None):
        """Set customer context for personalized responses"""
        if name:
            self.customer_context['name'] = name
        if email:
            self.customer_context['email'] = email
        if phone:
            self.customer_context['phone'] = phone
        if zipcode:
            self.customer_context['zipcode'] = zipcode
        if city:
            self.customer_context['city'] = city
        if preferred_type:
            self.customer_context['preferred_type'] = preferred_type
        if preferred_model:
            self.customer_context['preferred_model'] = preferred_model
        if preferred_trim:
            self.customer_context['preferred_trim'] = preferred_trim
    
    def get_response(self, user_input):
        """Get response from agent with current customer context"""
        # If agent missing (e.g., no API key), use fallback
        if not self.agent:
            return self._tool_fallback(user_input)

        # Try normal agent; on failure, fallback to tools
        try:
            return get_agent_response(self.agent, user_input, self.customer_context)
        except Exception as e:
            self._logger.warning(f"Agent error, using fallback: {e}")
            return self._tool_fallback(user_input)
    
    def reset_conversation(self):
        """Reset conversation memory"""
        if self.agent and hasattr(self.agent, 'memory'):
            self.agent.memory.clear()
    
    def get_conversation_history(self):
        """Get current conversation history"""
        if self.agent and hasattr(self.agent, 'memory'):
            return self.agent.memory.buffer
        return []


if __name__ == "__main__":
    # Test agent creation and basic functionality
    print("Testing Toyota AI Agent...")
    
    try:
        # Create agent manager
        manager = ToyotaAgentManager()
        
        # Set sample customer context
        manager.set_customer_context(
            name="John Doe", 
            email="john@example.com", 
            zipcode="90012"
        )
        
        # Test conversation
        print("\n1. Testing greeting:")
        response = manager.get_response("Hello, I'm interested in Toyota vehicles.")
        print(f"Agent: {response[:200]}...")
        
        print("\n2. Testing inventory search:")
        response = manager.get_response("What Toyota cars are available near me?")
        print(f"Agent: {response[:200]}...")
        
        print("\n✅ Agent testing completed!")
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        print("Please ensure OpenAI API key is set and all dependencies are installed.")