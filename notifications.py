# notifications.py
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Email configuration (using environment variables)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "your_app_password")


def send_email(to_email, subject, body, is_html=False):
    """Send email notification"""
    try:
        # Create message
        msg = MimeMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add body
        msg.attach(MimeText(body, 'html' if is_html else 'plain'))
        
        # Connect to server and send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, to_email, text)
        server.quit()
        
        print(f"✅ Email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        # For demo purposes, we'll print the email content
        print(f"📧 [DEMO EMAIL] To: {to_email}")
        print(f"📧 [DEMO EMAIL] Subject: {subject}")
        print(f"📧 [DEMO EMAIL] Body:\n{body}")
        print("-" * 50)
        return False


def send_customer_booking_confirmation(customer_data, vehicle_data, dealership_data, test_drive_data):
    """Send booking confirmation email to customer"""
    subject = f"Test Drive Confirmation - {vehicle_data['model']} {vehicle_data['trim']}"
    
    body = f"""
Dear {customer_data['name']},

Thank you for scheduling a test drive with Toyota! We're excited to help you experience the {vehicle_data['model']} {vehicle_data['trim']}.

🚗 Vehicle Details:
- Model: {vehicle_data['model']} {vehicle_data['trim']}
- Color: {vehicle_data['color']}
- Price: ${vehicle_data['rate']:,.2f}

📍 Dealership Information:
- Location: {dealership_data['name']}
- Address: {dealership_data['address']}, {dealership_data['city']} {dealership_data['zipcode']}
- Phone: {dealership_data['phone']}

📅 Test Drive Details:
- Date: {test_drive_data['date']}
- Time: {test_drive_data['time']}
- Special Requests: {test_drive_data.get('special_request', 'None')}

What to Bring:
- Valid driver's license
- Proof of insurance
- Comfortable driving attire

We look forward to seeing you soon! If you need to reschedule or have any questions, please contact us at {dealership_data['phone']}.

Best regards,
Toyota Sales Team
{dealership_data['name']}
    """
    
    return send_email(customer_data['email'], subject, body.strip())


def send_dealer_notification(customer_data, vehicle_data, dealership_data, test_drive_data, salesperson_email):
    """Send new test drive notification to dealer/salesperson"""
    subject = f"New Test Drive Appointment - {customer_data['name']}"
    
    body = f"""
New Test Drive Appointment Scheduled

👤 Customer Information:
- Name: {customer_data['name']}
- Email: {customer_data['email']}
- Phone: {customer_data['phone']}
- ZIP Code: {customer_data['zipcode']}

🚗 Vehicle Information:
- Model: {vehicle_data['model']} {vehicle_data['trim']}
- Color: {vehicle_data['color']}
- Price: ${vehicle_data['rate']:,.2f}
- VIN: {vehicle_data.get('vin', 'TBD')}

📅 Appointment Details:
- Date: {test_drive_data['date']}
- Time: {test_drive_data['time']}
- Special Requests: {test_drive_data.get('special_request', 'None')}

Please prepare the vehicle and contact the customer if needed.

Toyota Sales System
    """
    
    return send_email(salesperson_email, subject, body.strip())


def send_status_update_notification(customer_email, customer_name, status, vehicle_info, dealership_info):
    """Send test drive status update to customer"""
    status_messages = {
        'completed': 'Your test drive has been completed! We hope you enjoyed the experience.',
        'cancelled': 'Your test drive appointment has been cancelled. Please contact us to reschedule.',
        'rescheduled': 'Your test drive appointment has been rescheduled. Please check your new appointment details.',
        'no_show': 'We missed you at your scheduled test drive. Please contact us to reschedule.'
    }
    
    subject = f"Test Drive Update - {vehicle_info.get('model', 'Toyota')} {vehicle_info.get('trim', '')}"
    
    body = f"""
Dear {customer_name},

{status_messages.get(status, 'Your test drive status has been updated.')}

Vehicle: {vehicle_info.get('model', 'Toyota')} {vehicle_info.get('trim', '')}
Dealership: {dealership_info.get('name', '')}
Status: {status.title()}

If you have any questions or would like to schedule another test drive, please contact us at {dealership_info.get('phone', '')}.

Thank you for choosing Toyota!

Best regards,
Toyota Sales Team
    """
    
    return send_email(customer_email, subject, body.strip())


def send_feedback_request(customer_email, customer_name, vehicle_info, test_drive_id):
    """Send feedback request email after completed test drive"""
    subject = f"How was your {vehicle_info.get('model', 'Toyota')} test drive experience?"
    
    body = f"""
Dear {customer_name},

Thank you for test driving the {vehicle_info.get('model', 'Toyota')} {vehicle_info.get('trim', '')}! 

We'd love to hear about your experience. Your feedback helps us improve our service and helps other customers make informed decisions.

Please take a moment to share your thoughts:
- How was the vehicle performance?
- Did the car meet your expectations?
- How was our service quality?
- Any features you particularly liked or disliked?
- Overall rating (1-5 stars)?

You can reply to this email with your feedback, or visit our dealership to speak with our team.

If you're interested in purchasing this vehicle or would like to test drive other Toyota models, please don't hesitate to contact us!

Thank you for choosing Toyota!

Best regards,
Toyota Sales Team

Reference ID: TD-{test_drive_id}
    """
    
    return send_email(customer_email, subject, body.strip())


if __name__ == "__main__":
    # Test email functionality
    print("Testing email notifications...")
    
    # Sample data for testing
    customer_data = {
        'name': 'John Doe',
        'email': 'test@example.com',
        'phone': '555-1234',
        'zipcode': '90210'
    }
    
    vehicle_data = {
        'model': 'Camry',
        'trim': 'XSE',
        'color': 'Ruby Flare Pearl',
        'rate': 32000.0
    }
    
    dealership_data = {
        'name': 'Toyota of Beverly Hills',
        'address': '123 Luxury Ave',
        'city': 'Beverly Hills',
        'zipcode': '90210',
        'phone': '310-555-0100'
    }
    
    test_drive_data = {
        'date': '2025-10-20',
        'time': '2:00 PM',
        'special_request': 'Interested in hybrid features'
    }
    
    # Test emails
    send_customer_booking_confirmation(customer_data, vehicle_data, dealership_data, test_drive_data)
    send_dealer_notification(customer_data, vehicle_data, dealership_data, test_drive_data, "sales@toyota.com")