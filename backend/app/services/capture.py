from datetime import datetime, timezone
from io import BytesIO
from ipaddress import IPv4Address, IPv6Address
import math

import scapy.utils
from scapy.layers.inet import IP, TCP, UDP
from scapy.layers.inet6 import IPv6


class InvalidCapture(ValueError):
    pass


class CaptureLimitExceeded(ValueError):
    pass


def analyze_capture(content: bytes, filename: str, max_packets: int = 100000) -> dict:
    if not content:
        raise InvalidCapture("The capture file is empty.")
    flows: dict[tuple, dict] = {}
    packets_seen = 0
    supported_packets = 0
    captured_bytes = 0
    try:
        with scapy.utils.PcapReader(BytesIO(content)) as reader:
            for packet in reader:
                packets_seen += 1
                if packets_seen > max_packets:
                    raise CaptureLimitExceeded(f"Capture exceeds the {max_packets:,}-packet analysis limit.")
                ip = packet.getlayer(IP) or packet.getlayer(IPv6)
                tcp = packet.getlayer(TCP)
                udp = packet.getlayer(UDP)
                if ip is None or (tcp is None and udp is None):
                    continue
                protocol = "TCP" if tcp is not None else "UDP"
                source = str(IPv4Address(ip.src) if isinstance(ip, IP) else IPv6Address(ip.src))
                destination = str(IPv4Address(ip.dst) if isinstance(ip, IP) else IPv6Address(ip.dst))
                transport = tcp or udp
                source_endpoint = (source, int(transport.sport))
                destination_endpoint = (destination, int(transport.dport))
                endpoint_pair = tuple(sorted((source_endpoint, destination_endpoint)))
                key = (protocol, endpoint_pair)
                timestamp = float(packet.time)
                if not math.isfinite(timestamp) or not -62135596800 <= timestamp <= 253402300799:
                    raise InvalidCapture("The capture contains an invalid packet timestamp.")
                size = len(packet)
                flow = flows.get(key)
                if flow is None:
                    if len(flows) >= 10000:
                        raise CaptureLimitExceeded("Capture exceeds the 10,000-flow analysis limit.")
                    flow = flows[key] = {
                        "source": f"{source}:{source_endpoint[1]}",
                        "destination": f"{destination}:{destination_endpoint[1]}",
                        "source_endpoint": source_endpoint,
                        "protocol": protocol,
                        "packets": 0,
                        "captured_bytes": 0,
                        "source_packets": 0,
                        "destination_packets": 0,
                        "source_bytes": 0,
                        "destination_bytes": 0,
                        "first_seen_epoch": timestamp,
                        "last_seen_epoch": timestamp,
                    }
                forward = source_endpoint == flow["source_endpoint"]
                flow["packets"] += 1
                flow["captured_bytes"] += size
                flow["source_packets" if forward else "destination_packets"] += 1
                flow["source_bytes" if forward else "destination_bytes"] += size
                flow["first_seen_epoch"] = min(flow["first_seen_epoch"], timestamp)
                flow["last_seen_epoch"] = max(flow["last_seen_epoch"], timestamp)
                supported_packets += 1
                captured_bytes += size
    except (CaptureLimitExceeded, InvalidCapture):
        raise
    except Exception as exc:
        raise InvalidCapture("The file is not a supported or readable PCAP/PCAPNG capture.") from exc

    if not packets_seen:
        raise InvalidCapture("The capture contains no packets.")
    results = []
    for flow in sorted(flows.values(), key=lambda item: item["first_seen_epoch"]):
        first = flow.pop("first_seen_epoch")
        last = flow.pop("last_seen_epoch")
        flow.pop("source_endpoint")
        flow["duration_seconds"] = max(0.0, last - first)
        flow["first_seen"] = datetime.fromtimestamp(first, timezone.utc).isoformat()
        flow["last_seen"] = datetime.fromtimestamp(last, timezone.utc).isoformat()
        results.append(flow)
    return {
        "filename": filename,
        "packets_seen": packets_seen,
        "supported_packets": supported_packets,
        "flow_count": len(results),
        "captured_bytes": captured_bytes,
        "flows": results[:500],
        "limitations": [
            "Flow summaries are derived from this uploaded capture and are not live interface monitoring.",
            "These packet-derived fields do not match the evaluated UNSW-NB15 model schema and are not sent to the ML classifier.",
            "Only TCP and UDP over IPv4/IPv6 are summarized; other packet types are counted but not classified.",
        ],
    }
