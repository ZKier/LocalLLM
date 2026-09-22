from datetime import datetime

ts = 1760936400000000
# Divide by 1 million to get seconds
dt_object = datetime.fromtimestamp(ts / 1000000)

print(f"The date is: {dt_object.strftime('%A, %B %d, %Y')}")