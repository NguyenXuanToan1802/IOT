Outside:
1. Tìm ip của Laptop: Mở command prompt, sử dụng lệnh ipconfig tìm ip.
2. Mở file outside.py trên laptop, thay đổi giá trị biến server_ip bằng ip của Laptop.
3. Chạy file outside.py để làm homecenter cho coap
4. Mở file outside.ino trong folder outside, thay đổi thông tin wifi cùng wifi với Laptop (ssid và password). Thay đổi giá trị biến serverip bằng ip của laptop vừa tìm được.
5. Nạp code file outside.ino cho esp8266, cắm nguồn cho esp8266, sau đó hệ thống sẽ tự vận hành.
Inside:
1. Tìm ip của Laptop: Mở command prompt, sử dụng lệnh ipconfig tìm ip.
2. Mở file inside.py trên laptop, thay đổi giá trị biến MQTT_BROKER_HOST bằng ip của Laptop.
3. Chạy file inside.py để làm homecenter cho mqtt
4. Mở file inside.ino trong folder inside, thay đổi thông tin wifi cùng wifi với Laptop (ssid và password). Thay đổi giá trị biến mqtt_server bằng ip của laptop vừa tìm được.
5. Nạp code file inside.ino cho esp8266, cắm nguồn cho esp8266, sau đó hệ thống sẽ tự vận hành.
Thingsboard:
1. Truy cập vào đường dẫn: https://thingsboard.hust-2slab.org/dashboard/43c6e470-ad49-11ee-b092-a16205cf5a8e?publicId=4d66ea20-ac77-11ee-b092-a16205cf5a8e