import logging, time, os, signal, re, string
from autotest_lib.client.common_lib import error
from autotest_lib.client.bin import utils
from autotest_lib.client.virt import virt_utils

def check_iorate(vm_name, session, io_limits):
    """
    KVM guest I/O rate check:
    3) Execute benchmarks of disk io limits
    4) Made a regexp search on dd output to isolate the throughput, convert
it to an float
    5) Compare with the desired value, failing it if the criteria is not
met.
    6) Close the session

    @param vm_name: vm name 
    @param session: session with each guest
    @param io_limits: I/O rate limits.    
    """
    try:
        output = session.cmd_output('dd if=/dev/vda of=/dev/null bs=256K count=128 iflag=direct')
        bps_bytes = re.findall(r'[0-9]* bytes', output)
        if not bps_bytes:
            raise error.TestFail('Fail to get I/O bytes at runtime.')

        bps_seconds = re.findall(r'[0-9]*[.][0-9]* s', output)
        if not bps_seconds:
            raise error.TestFail('Fail to get I/O seconds at runtime.')

        bps_bytes = string.join(bps_bytes)
        bps_bytes = bps_bytes.replace(' bytes','')
        bps_bytes = float(bps_bytes)

        bps_seconds = string.join(bps_seconds)
        bps_seconds = bps_seconds.replace(' s','')
        bps_seconds = float(bps_seconds)
        if bps_seconds == 0:
            raise error.TestFail('The I/O seconds at runtime is zero.')

        logging.debug("VM: %s, bps_bytes: %d, bps_seconds: %f", vm_name, bps_bytes, bps_seconds)
        bps_iorate = (bps_bytes / (1024 * 1024)) / bps_seconds

        logging.debug("VM: %s, io_limits: %f, bps_iorate: %f", vm_name, io_limits, bps_iorate)
        if bps_iorate > io_limits:
            logging.error("VM: %s, FAIL, exceed disk I/O limit", vm_name)
        else:
            logging.info("VM: %s, PASS, meet disk I/O limit", vm_name)
    finally:
        session.close()
	return

def run_disk_io_limits(test, params, env):
    """
    KVM guest I/O limits test:
    1) Get a VM object
    2) Log into a guest
    3) Execute benchmarks of disk io limits
    4) Made a regexp search on dd output to isolate the throughput, convert
it to an float 
    5) Compare with the desired value, failing it if the criteria is not
met.
    6) Close the session

    @param test: kvm test object
    @param params: Dictionary with the test parameters
    @param env: Dictionary with test environment.
    """

    # Log into all VMs
    login_timeout = int(params.get("login_timeout", 360))
    vms = []
    sessions = []
    for vm_name in params.objects("vms"):
        vms.append(env.get_vm(vm_name))
        vms[-1].verify_alive()
        sessions.append(vms[-1].wait_for_login(timeout=login_timeout))

    # The default unit of io_limits is MB/s
    io_limits = params.get("io_limits", "100 MB/s")
    io_limits = re.findall(r'[0-9]* MB\/s', io_limits)
    if not io_limits:
      	raise error.TestFail('Fail to get I/O rate limit.')

    io_limits = string.join(io_limits)
    io_limits = io_limits.replace(' MB/s','')
    io_limits = float(io_limits)

    virt_utils.parallel((check_iorate, (vm_name, session, io_limits))
                       for vm_name, session in zip(params.objects("vms"), sessions))
