import asyncio
import ssl
import time
import random

from config import CONNECT_TIMEOUT, READ_TIMEOUT

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# کش برای دامنه‌های موفق
SUCCESS_DOMAINS = {}

async def probe(ip, domain, port):
    start = time.perf_counter()
    
    # تایم‌اوت پویا بر اساس موفقیت قبلی دامنه
    dynamic_timeout = CONNECT_TIMEOUT
    if domain in SUCCESS_DOMAINS:
        dynamic_timeout = max(1, SUCCESS_DOMAINS[domain] / 1000)  # بر حسب میلی‌ثانیه
    
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                ip,
                port,
                ssl=SSL_CTX,
                server_hostname=domain
            ),
            timeout=dynamic_timeout
        )
        
        # استفاده از HEAD درخواست سبک
        req = (
            f"HEAD / HTTP/1.1\r\n"
            f"Host: {domain}\r\n"
            f"User-Agent: CleanIPScanner/3.0\r\n"
            f"Connection: close\r\n\r\n"
        )
        
        writer.write(req.encode())
        await writer.drain()
        
        # فقط خواندن هدر (۵۱۲ بایت کافی است)
        response = await asyncio.wait_for(
            reader.read(512),
            timeout=READ_TIMEOUT
        )
        
        latency = (time.perf_counter() - start) * 1000
        
        writer.close()
        try:
            await writer.wait_closed()
        except:
            pass
        
        # هر پاسخ HTTP معتبر است (حتی ۴۰۳، ۵۰۰)
        valid = b"HTTP/" in response
        
        # به‌روزرسانی کش دامنه
        if valid and domain in SUCCESS_DOMAINS:
            SUCCESS_DOMAINS[domain] = (SUCCESS_DOMAINS[domain] + latency) / 2
        elif valid:
            SUCCESS_DOMAINS[domain] = latency
        
        return {
            "tls": True,
            "http": valid,
            "latency": latency
        }
        
    except asyncio.TimeoutError:
        return None
    except Exception:
        return None
