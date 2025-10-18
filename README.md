# 🚗 Toyota AI Sales Assistant

A comprehensive AI-powered sales assistant for Toyota Automobiles North America, built with LangChain, OpenAI, Serper API, and Streamlit. The system helps customers explore vehicles, check inventory, and schedule test drives while providing an admin dashboard for dealership management.

## 🌟 Features

### Customer Interface
- **AI Chat Assistant**: Natural conversation with Toyota AI agent
- **Inventory Search**: Find available vehicles by ZIP code
- **Vehicle Information**: Detailed specs, features, and pricing
- **Test Drive Scheduling**: Easy booking with automated confirmations
- **Vehicle Cards**: Visual display of available inventory
- **Memory Persistence**: Maintains context throughout conversation

### Admin Dashboard
- **Inventory Management**: View and update vehicle availability
- **Test Drive Management**: Track and update appointment status
- **Analytics**: Summary statistics and popular vehicle insights
- **Automated Notifications**: Email updates for status changes
- **Dealership Information**: Complete dealer and salesperson directory

### AI Agent Capabilities
- **LangChain ReAct Framework**: Intelligent tool selection and reasoning
- **Serper API Integration**: Real-time Toyota vehicle information
- **Database Tools**: Query inventory and save bookings
- **Email Automation**: Customer and dealer notifications
- **Conversation Memory**: Context-aware responses

## 🛠️ Technology Stack

- **Backend**: Python, LangChain, OpenAI GPT-4
- **Frontend**: Streamlit
- **Database**: SQLite with comprehensive schema
- **APIs**: OpenAI, Serper (Google Search)
- **Email**: SMTP with automated templates
- **Memory**: ConversationBufferMemory for context

## 📦 Installation

1. **Clone the repository**
   ```bash
   cd C:\Agentic_AI_Testdrive\test_drive
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   copy .env.template .env
   # Edit .env file with your API keys
   ```

4. **Initialize database**
   ```bash
   python database_setup.py
   ```

## 🚀 Quick Start

1. **Start the application**
   ```bash
   streamlit run main.py
   ```

2. **Access the platform**
   - Open your browser to `http://localhost:8501`
   - Choose between Customer Chat or Admin Dashboard

3. **Customer Interface**
   - Enter customer information in the sidebar
   - Chat with the Toyota AI assistant
   - Browse available inventory
   - Schedule test drives

4. **Admin Interface**
   - View analytics dashboard
   - Manage inventory status
   - Update test drive appointments
   - Send customer notifications

## 🔑 Environment Variables

### Required
- `OPENAI_API_KEY`: OpenAI API key for GPT-4 access

### Optional
- `SERPER_API_KEY`: Serper API key for enhanced vehicle information
- `SENDER_EMAIL`: Email address for notifications
- `SENDER_PASSWORD`: Email app password for SMTP
- `SMTP_SERVER`: SMTP server (default: smtp.gmail.com)
- `SMTP_PORT`: SMTP port (default: 587)

## 📊 Database Schema

### Core Tables
- **Dealership**: Store locations and contact information
- **Salesperson**: Sales team assigned to dealerships
- **Vehicle**: Toyota model catalog with features and pricing
- **Inventory**: Available vehicles at each dealership
- **Customer**: Customer information and preferences
- **TestDrive**: Appointment bookings and status
- **Feedback**: Customer experience ratings and comments

### Sample Data Included
- 5 dealerships across major US cities
- 18+ Toyota vehicles (sedans, SUVs, hybrids, trucks)
- Complete inventory with VIN numbers
- Sales team contacts

## 🤖 AI Agent Behavior

The Toyota AI Sales Agent:
- **Focuses exclusively on Toyota vehicles**
- **Gathers customer preferences** (budget, needs, location)
- **Uses tools intelligently** for search, inventory, and booking
- **Maintains conversation context** throughout interaction
- **Proactively suggests test drives** when appropriate
- **Provides accurate, verified information** only

### Agent Tools
1. **search_toyota_info**: External vehicle research via Serper API
2. **search_inventory**: Find available vehicles by location
3. **get_vehicle_details**: Detailed vehicle information
4. **save_test_drive**: Process booking requests with notifications

## 📧 Email Workflow

### Booking Confirmations
- **Customer Email**: Booking details, dealership info, preparation tips
- **Dealer Email**: Customer information, vehicle details, appointment

### Status Updates
- **Completion**: Thank you + feedback request
- **Cancellation**: Polite notification + rescheduling options
- **No-show**: Friendly follow-up + new appointment offer

## 📱 User Experience

### Customer Journey
1. **Information Gathering**: Name, email, phone, ZIP code
2. **Vehicle Exploration**: Chat about needs and preferences
3. **Inventory Display**: Visual cards with available vehicles
4. **Detailed Information**: Specs, features, and pricing
5. **Test Drive Booking**: Simple form with date/time selection
6. **Confirmation**: Automated emails and preparation instructions

### Admin Workflow
1. **Dashboard Overview**: Key metrics and recent activity
2. **Inventory Management**: Update availability and status
3. **Appointment Tracking**: Monitor test drive schedule
4. **Status Updates**: Change appointment status with auto-notifications
5. **Analytics**: Popular vehicles and conversion insights

## 🔧 Customization

### Adding New Vehicles
```python
# In database_setup.py, add to SAMPLE_VEHICLES
new_vehicle = ("Toyota", "Model", "Trim", "Color", price, features_json)
```

### Custom Email Templates
```python
# Modify functions in notifications.py
def send_custom_notification(customer_data, message):
    # Your custom email logic
```

### Additional Tools
```python
# In tools.py, create new LangChain tools
custom_tool = Tool(
    name="custom_function",
    description="Description for the AI agent",
    func=your_function
)
```

## 🚨 Troubleshooting

### Common Issues
1. **OpenAI API Key**: Ensure valid key in .env file
2. **Database Errors**: Run `python database_setup.py` to reinitialize
3. **Email Notifications**: Check SMTP settings and app passwords
4. **Serper API**: Optional - app works without it

### Debug Mode
```python
# Set verbose=True in agent.py for detailed logging
agent = initialize_agent(..., verbose=True)
```

## 📈 Future Enhancements

- **Multi-language support**
- **Voice interface integration**
- **Advanced analytics dashboard**
- **CRM system integration**
- **Mobile app version**
- **Real-time inventory sync**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your enhancement
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is developed for Toyota Automobiles North America. All Toyota trademarks and vehicle names are property of Toyota Motor Corporation.

## 📞 Support

For technical support or feature requests, please contact the development team or create an issue in the repository.

---

**Built with ❤️ for Toyota customers and dealers**
*Enhancing the car buying experience through AI innovation*