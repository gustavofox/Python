import argparse
from textwrap import dedent

from scapy.all import *


class ScannerStatus(object):
    OPEN = "Open"
    CLOSED = "Closed"
    FILTERED = "Filtered"


class Scanner(object):
    def __init__(self, timeout):
        self.timeout = timeout

    def arp_ping(self, subnet):
        """ARP Pings entire subnet returns found in subnet."""
        conf.verb = 0
        answered, unanswered = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=subnet), timeout=self.timeout, verbose=False, inter=0.1)
        return [rcv.sprintf(r"%Ether.src% - %ARP.psrc%") for snd, rcv in answered]

    def _tcp_default(self, dst_ip, dst_port, src_port):
        """Default TCP Scan."""
        default_scan = sr1(IP(dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags="S"), timeout=self.timeout)
        if default_scan is not None:
            if default_scan.getlayer(TCP).flags == 0x12:
                send_rst = sr(IP(dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags="AR"), timeout=self.timeout)
                return ScannerStatus.OPEN
        return ScannerStatus.CLOSED

    def _tcp_stealth(self, dst_ip, dst_port, src_port):
        """Stealthy TCP Scan"""
        stealth_scan = sr1(IP(dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags="S"), timeout=self.timeout)
        if stealth_scan is not None:
            if stealth_scan.getlayer(TCP).flags == 0x12:
                send_rst = sr(IP(dst=dst_ip)/TCP(sport=src_port, dport=dst_port, flags="R"), timeout=self.timeout)
                return ScannerStatus.OPEN
            elif stealth_scan.getlayer(TCP).flags == 0x14:
                return ScannerStatus.CLOSED
        return ScannerStatus.FILTERED

    def tcp(self, dst_ip, dst_port, stealth=False):
        src_port = RandShort()
        fn = self._tcp_stealth if stealth else self._tcp_default
        return fn(dst_ip, dst_port, src_port)

    def tcp_scan(self, dst_ip, ports, stealth=False):
        """Scans TCP ports for availability."""
        for dst_port in ports:
            yield port, self.tcp(dst_ip, dst_port, stealth)


def parse_arguments():
    """Arguments parser."""
    parser = argparse.ArgumentParser(usage='%(prog)s [options] <subnet>',
                                     description='port scanning tool @Ludisposed',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=dedent('''\
                                        Examples:
                                        python port_scan.py "192.168.1.0/24" -s
                                        python port_scan.py "192.168.1.0/24" --timeout 10'''))
    parser.add_argument('-s', '--stealth', default=False, action="store_true", help='Stealthy TCP scan')
    parser.add_argument('--timeout', type=int, default=2, help='Timeout parameter of scans')
    parser.add_argument('subnet', type=str, help='Subnet in from of [ip/bitmask]')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    scanner = Scanner(args.timeout)

    system_ports = {20: 'FTP',
                    21: 'FTP Control',
                    22: 'SSH',
                    23: 'Telnet',
                    25: 'SMPT',
                    53: 'DNS',
                    67: 'DHCP Server',
                    68: 'DHCP Client',
                    69: 'TFTP',
                    80: 'HTTP',
                    110: 'POP3',
                    119: 'NNTP',
                    139: 'NetBIOS',
                    143: 'IMAP',
                    389: 'LDAP',
                    443: 'HTTPS',
                    445: 'SMB',
                    465: 'SMTP',
                    569: 'MSN',
                    587: 'SMTP',
                    990: 'FTPS',
                    993: 'IMAP',
                    995: 'POP3'}

    user_ports = {1080: 'SOCKS',
                  1194: 'OpenVPN',
                  3306: 'MySQL',
                  3389: 'RDP',
                  3689: 'DAAP',
                  5432: 'PostGreSQL',
                  5800: 'VNC',
                  5900: 'VNC',
                  6346: 'Grutella',
                  8080: 'HTTP'}

    conf.verb = 0
    network = scanner.arp_ping(args.subnet)
    scan_type = 'stealth' if args.stealth else 'default'
    for connection in network:
        mac, ip = connection.split(' - ')
        print('\n\n[!] Trying port scan of current connection with mac={} and ip={}'.format(mac, ip))
        print('[!] User Ports')
        for port, status in scanner.tcp_scan(ip, user_ports.keys(), args.stealth):
            print('[*] TCP {} scan: dest_ip={} port={}, service={}, status={}'
                  .format(scan_type, ip, port, user_ports[port], status))

        print('[!] System Ports')
        for port, status in scanner.tcp_scan(ip, system_ports.keys(), args.stealth):
            print('[*] TCP {} scan: dest_ip={} port={}, service={}, status={}'
                  .format(scan_type, ip, port, system_ports[port], status))
