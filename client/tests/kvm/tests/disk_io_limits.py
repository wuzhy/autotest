import logging, time, os, re, string
from autotest_lib.client.common_lib import error
from autotest_lib.client.bin import utils
from autotest_lib.client.virt import virt_utils


def run_disk_io_limits(test, params, env):
    """
    KVM guest stop test:
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
    vm = env.get_vm(params["main_vm"])
    vm.verify_alive()
    #timeout = float(params.get("login_timeout", 240))
    #session = vm.wait_for_login(timeout=timeout)
    session = vm.wait_for_login(timeout=30)

    io_limits = params.get("io_limits", "10")

    try:
	output = session.cmd_output('dd if=/dev/vda of=/dev/null bs=256K count=128 iflag=direct')
	bps_bytes = re.findall(r'[0-9]*.[0-9]* GB\/s', output)
	bps_bytes = string.join(bps_bytes)
	bps_bytes.replace(' GB/s','')
	bps_bytes = float(bps_bytes)

        if bps_bytes > io_limits:
           raise error.TestFail('Throughput bigger than the stablished treshold of 10 MB/s')
	else:
	   logging.info("The limit crteria is met...")
    finally:
        session.close()
