import logging
from datetime import datetime, timedelta, date, timezone

import aniso8601
from database.connection import get_cursor

from mail.send import send_mail
from mail.templates import EmailTemplates

LOGGER = logging.getLogger(__name__)

def _get_active_prescriptions() -> list: #pragma: no cover
    with get_cursor() as cursor:
        cursor.execute("""SELECT prescription_id, time_statement, username, users.name, users.email, m.medication_name, short_code FROM repeat_prescriptions
                        JOIN users USING (username)
                        JOIN medications m USING (medication_id)
                        WHERE approved_at is not null;""")
        return cursor.fetchall()

def check_for_valid_prescriptions(prescription): #pragma: no cover
    """ Callback to filter a list of prescriptions
        which require the user be notified
    """
    period = aniso8601.parse_repeating_interval(prescription['time_statement'])
    LOGGER.debug(period)

    for p in period:
        if type(p) == datetime:
            LOGGER.debug('Found datetime object')
            difference_from_today = datetime.now(timezone.utc) - p
        else:
            LOGGER.debug('Found date object')
            difference_from_today = date.today() - p
        # if today is 10 days from the period end.
        if difference_from_today.days == 10:
            return True
        # else if it is greater or less than the maximum days in the month,
        # there is no need to iterate any further. Lets exit out of the loop.
        elif difference_from_today.days > 31 or difference_from_today.days < -31:
            return False


def process_prescription_notifications():
    """ Process the reminder notifications for repeat prescriptions """
    prescriptions_relevant = [x for x in filter(check_for_valid_prescriptions, _get_active_prescriptions())]

    for prescription in prescriptions_relevant:
        LOGGER.info('Sending prescription notification to %s', prescription['username'])
        send_mail(
            email=prescription['email'],
            name=prescription['name'],
            template_id=EmailTemplates.PRESCRIPTION_NOTIFICATION.value,
            template_object={
                'medication_name': prescription['medication_name'],
                'patient_name': prescription['name'],
                'short_code': prescription['short_code']
            }
        )
