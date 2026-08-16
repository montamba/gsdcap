from datetime import datetime, timedelta

expired = datetime.now()+timedelta(hours=2)

print(expired > datetime.now())