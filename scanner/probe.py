import asyncio
import ssl
import time

from config import CONNECT_TIMEOUT, READ_TIMEOUT

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

async def probe(ip, domain, port):
    start = time.perf_counter()

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(
                ip,
                port,
                ssl=SSL_CTX,
                server_hostname=domain
            ),
            timeout=CONNECT_TIMEOUT
        )

        req = (
            f"HEAD / HTTP/1.1\r\n"
            f"Host: {domain}\r\n"
            f"User-Agent: CleanIPScanner/2.0\r\n"
            f"Connection: close\r\n\r\n"
        )

        writer.write(req.encode())
        await writer.drain()

        response = await asyncio.wait_for(
            reader.read(2048),
            timeout=READ_TIMEOUT
        )

        latency = (time.perf_counter() - start) * 1000

        writer.close()

        try:
            await writer.wait_closed()
        except Exception:
            pass

        valid_http = (
            b"HTTP/" in response and (
                b"200" in response or
                b"301" in response or
                b"302" in response
            )
        )

        return {
            "tls": True,
            "http": valid_http,
            "latency": latency
        }

    except Exception:
        return None
