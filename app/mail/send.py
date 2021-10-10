""" Module to handle sending of emails to users. """
from sendgrid.helpers.mail import Mail
from sendgrid import SendGridAPIClient

from config import SENDGRID_API_KEY, SENDGRID_HOST, MAIL_FROM_ADDRESS

def send_mail(email: str, name: str, template_id: str, template_object: dict = {}):
    """ Send an email to a user """
    TO_EMAILS = [(email, name)]

    message = Mail(
        from_email=MAIL_FROM_ADDRESS,
        to_emails=TO_EMAILS
    )

    message.dynamic_template_data = {
        **template_object
    }
    message.template_id = template_id

    sg = SendGridAPIClient(host=SENDGRID_HOST, api_key=SENDGRID_API_KEY)

    sg.send(message)
