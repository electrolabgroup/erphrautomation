# local_config.py
START_DATE = "2024-10-10"
END_DATE = "2024-11-12"

ERPNEXT_API_KEY = '53be8c72ce2399c'
ERPNEXT_API_SECRET = 'a3f8beb819ccbef'
ERPNEXT_URL = 'http://212.47.244.14/'


devices = [
    {'device_id': '3', 'ip': '192.168.0.209', 'punch_direction': None, 'clear_from_device_on_fetch': False},
    {'device_id': '1', 'ip': '192.168.4.9', 'punch_direction': None, 'clear_from_device_on_fetch': False}
]

SHIFT = ["Goregaon","Day"]


# devices = [
#     {'device_id': '1', 'ip': '192.168.4.9', 'punch_direction': None, 'clear_from_device_on_fetch': False},
#     {'device_id': '2', 'ip': '192.168.2.9', 'punch_direction': None, 'clear_from_device_on_fetch': False},
#     {'device_id': '3', 'ip': '192.168.0.209', 'punch_direction': None, 'clear_from_device_on_fetch': False}
# ]

# SHIFT = ["Day", "Mahape", "Goregaon"]
# devices = [
#     {'device_id': '2', 'ip': '192.168.2.9', 'punch_direction': None, 'clear_from_device_on_fetch': False},
# ]
# SHIFT = "Mahape"