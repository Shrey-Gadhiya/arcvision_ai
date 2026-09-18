import urllib.request
import json

# Login as admin
login_data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=login_data, headers={'Content-Type': 'application/json'})
resp = json.loads(urllib.request.urlopen(req).read().decode())
token = resp['access_token']
print('Authenticated as admin')

# Add camera for sample.mp4
cam_payload = json.dumps({
    'name': 'CAM-05: User Field Surveillance Feed',
    'description': 'Real-time multi-person field surveillance from root sample.mp4',
    'rtsp_url': 'E:/Project/187-last/sample.mp4',
    'stream_type': 'FILE',
    'group_name': 'Field Surveillance',
    'location': 'Sector 4 - Tactical Area Bravo',
    'latitude': 26.8540,
    'longitude': 85.2050,
    'heading_deg': 135.0,
    'fov_angle': 85.0,
    'target_fps': 15
}).encode()

req2 = urllib.request.Request('http://127.0.0.1:8000/api/v1/cameras/', data=cam_payload, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
res2 = json.loads(urllib.request.urlopen(req2).read().decode())
cam_id = res2['id']
print(f'Successfully added camera #{cam_id}: {res2["name"]}')

# Add restricted zone to CAM-05
zone_payload = json.dumps({
    'camera_id': cam_id,
    'name': 'Restricted Perimeter Zone',
    'zone_type': 'RESTRICTED',
    'points_json': json.dumps([{'x': 0.1, 'y': 0.3}, {'x': 0.9, 'y': 0.3}, {'x': 0.9, 'y': 0.9}, {'x': 0.1, 'y': 0.9}]),
    'color_hex': '#EF4444',
    'loitering_time_sec': 10
}).encode()
req3 = urllib.request.Request('http://127.0.0.1:8000/api/v1/zones/', data=zone_payload, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
res3 = json.loads(urllib.request.urlopen(req3).read().decode())
print(f'Added Zone to Camera #{cam_id}: {res3["name"]}')

# Add virtual fence tripwire to CAM-05
wire_payload = json.dumps({
    'camera_id': cam_id,
    'name': 'Virtual Perimeter Fence',
    'line_json': json.dumps({'start': {'x': 0.1, 'y': 0.5}, 'end': {'x': 0.9, 'y': 0.5}}),
    'direction': 'BIDIRECTIONAL',
    'color_hex': '#F59E0B'
}).encode()
req4 = urllib.request.Request('http://127.0.0.1:8000/api/v1/zones/tripwires', data=wire_payload, headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
res4 = json.loads(urllib.request.urlopen(req4).read().decode())
print(f'Added Virtual Fence Tripwire to Camera #{cam_id}: {res4["name"]}')
