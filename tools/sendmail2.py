import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def sendmail(_from, to, subject, html, text, smtp_host, smtp_user, smtp_pass):
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = _from
    msg['To'] = to
    
    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    
    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)
    msg.attach(part2)
    
    # Send the message via local SMTP server.
    s = smtplib.SMTP(smtp_host, 587, 'amcat-sql2.vu.nl')
    s.login(smtp_user, smtp_pass)
    
    # sendmail function takes 3 arguments: sender's address, recipient's address
    # and message to send - here it is sent as one string.
    print s.sendmail(_from, to, msg.as_string())
    print s.quit()
