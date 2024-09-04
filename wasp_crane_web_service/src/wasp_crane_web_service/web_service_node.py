#!/usr/bin/env python3
import rospy
import json
import requests
import subprocess
from std_msgs.msg import Int64
from wasp_crane_web_service.srv import SetFeedrate, SetFeedrateResponse, SetFlowrate, SetFlowrateResponse


class WebServiceNode:

    def __init__(self) -> None:
        rospy.init_node("web_service_node", anonymous=True)
        rospy.on_shutdown(self.shutdown)
        self.host = rospy.get_param("/host", default="192.168.0.159")
        self.headers = {
            "Host": "iaac",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Api-Key": "F4B968EDF7524DE4BD47E30063D17EE6",
        }
        self.printer_pos_url = "http://{0}/api/printer/pos".format(self.host)

        self.printer_pos_pub = rospy.Publisher("/printer_pos", Int64, queue_size=10)
        self.rate = rospy.Rate(10)

    def _test_connection(self) -> bool:
        try:
            subprocess.check_output(["ping", "-c", "1", self.host], timeout=5)
            return True
        except subprocess.CalledProcessError:
            rospy.logerr(f"[IAAC CRANE WEB CLIENT]: Ping failed: Unable to reach {self.host}")
            return False
        except subprocess.TimeoutExpired:
            rospy.logerr("[IAAC CRANE WEB CLIENT]: Ping failed: Timeout expired")
            return False

    def _init_services(self) -> None:
        rospy.Service("/iaac_crane/set_feedrate", SetFeedrate, self.set_feedrate_cb)
        rospy.Service("/iaac_crane/set_flowrate", SetFlowrate, self.set_flowrate_cb)

    def run(self) -> None:
        while not rospy.is_shutdown():
            filepos = self.retreive_job_progress()
            self.printer_pos_pub.publish(filepos)
            self.rate.sleep()

    def set_feedrate_cb(self, new_feedrate) -> SetFeedrateResponse:
        resp = requests.post(
            f"http://{self.host}/api/printer/printhead",
            headers=self.headers,
            data=json.dumps({"command": "flowrate", "factor": new_feedrate}),
        )
        if resp.status_code == 204:
            rospy.loginfo(f"[IAAC CRANE WEB CLIENT]: Feedrate set to {new_feedrate}")
            return SetFeedrateResponse(success=True)

    def set_flowrate_cb(self, new_flowrate) -> SetFlowrateResponse:
        resp = requests.post(
            f"http://{self.host}/api/printer/tool",
            headers=self.headers,
            data=json.dumps({"command": "flowrate", "factor": new_flowrate}),
        )
        if resp.status_code == 204:
            rospy.loginfo(f"[IAAC CRANE WEB CLIENT]: Flowrate set to {new_flowrate}")
            return SetFlowrateResponse(success=True)

    def shutdown(self) -> None:
        rospy.loginfo("[IAAC CRANE WEB CLIENT]: Shutting down...")
        rospy.signal_shutdown("Shutting down...")

    def retreive_job_progress(self) -> int:
        response = requests.get(
            f"http://{self.host}/api/job",
            headers=self.headers,
        )
        data = response.json()
        if response.status_code != 200:
            rospy.logerr("[IAAC CRANE WEB CLIENT]: Failed to get job progress")
            return None
        return data.get("progress", {}).get("filepos", None)


if __name__ == "__main__":
    try:
        web_service_node = WebServiceNode()
        web_service_node.run()
    except rospy.ROSInterruptException:
        pass
