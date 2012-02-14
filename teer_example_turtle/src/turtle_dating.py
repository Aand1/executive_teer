#!/usr/bin/env python
import math
import roslib; roslib.load_manifest('teer_example_turtle')
import rospy
import numpy as np
from turtlesim.msg import Velocity
from turtlesim.msg import Pose
from turtlesim.srv import TeleportAbsolute
from turtlesim.srv import SetPen
from turtlesim.srv import Spawn
from std_srvs.srv import Empty as EmptyServiceCall
from turtle_math import *
import rosteer
from teer import *

turtle1_velocity = None
turtle2_velocity = None
turtle1_set_pen = None
turtle2_set_pen = None

class TurtleScheduler(rosteer.ROSScheduler):
	""" A teer scheduler working with ROS """
	
	turtle1_pose = rosteer.ROSConditionVariable(None)
	turtle2_pose = rosteer.ROSConditionVariable(None)
	
	def __init__(self):
		""" Init the ROS scheduler """
		super(TurtleScheduler,self).__init__()

def turtle1_go(sched, target):
	""" Make turtle1 go to target, giving new speed command every second """
	while True:
		# set new speed commands
		turtle1_velocity.publish(control_command(sched.turtle1_pose, target, 1.0))
		# wait for 1 s
		yield WaitDuration(1)

def turtle2_go(sched, target):
	""" Make turtle1 go to target, giving new speed command every second """
	while True:
		# set new speed commands
		turtle2_velocity.publish(control_command(sched.turtle2_pose, target, 0.7))
		# wait for 1 s
		yield WaitDuration(1)

def turtle1_wandering(sched):
	""" Make turtle1 do a square in the environment """
	yield WaitCondition(lambda: sched.turtle1_pose is not None)
	
	targets = [(2,2), (9,2), (9,9), (2,9)]
	target_id = 0
	while True:
		print ('Going to ' + str(targets[target_id]))
		target = targets[target_id]
		go_tid =  yield NewTask(turtle1_go(sched, target))
		yield WaitCondition(lambda: dist(sched.turtle1_pose, target) < 0.1)
		yield KillTask(go_tid)
		target_id = (target_id + 1) % len(targets)

def turtle2_wandering(sched):
	""" Make turtle2 do a square in the environment, reverse direction as turtle1 """
	yield WaitCondition(lambda: sched.turtle2_pose is not None)
	
	targets = [(2,9), (9,9), (9,2), (2,2)]
	target_id = 0
	while True:
		print ('Going to ' + str(targets[target_id]))
		target = targets[target_id]
		go_tid =  yield NewTask(turtle2_go(sched, target))
		yield WaitCondition(lambda: dist(sched.turtle2_pose, target) < 0.1)
		yield KillTask(go_tid)
		target_id = (target_id + 1) % len(targets)

def cupidon():
	""" When turtles are close, make them dance """
	my_tid = yield GetTid()
	while True:
		yield  WaitCondition(lambda: dist(sched.turtle1_pose, sched.turtle2_pose) < 1)
		print 'Found friend, let\'s dance'
		other_tids = yield GetTids()
		other_tids.remove(my_tid)
		paused_tasks = yield PauseTasks(other_tids)
		turtle1_set_pen(255,0,0,0,0)
		turtle2_set_pen(0,255,0,0,0)
		for i in range(7):
			turtle1_velocity.publish(Velocity(1, 1))
			turtle2_velocity.publish(Velocity(1, -1))
			yield WaitDuration(0.9)
		turtle1_set_pen(0,0,0,0,1)
		turtle2_set_pen(0,0,0,0,1)
		print 'Tired of dancing, going back to wandering'
		resumed_tasks = yield ResumeTasks(other_tids)
		yield WaitDuration(10)

def turtle1_pose_updated(new_pose):
	""" We received a new pose of turtle1 from turtlesim, update condition variable in scheduler """
	global sched
	sched.turtle1_pose = new_pose

def turtle2_pose_updated(new_pose):
	""" We received a new pose of turtle2 from turtlesim, update condition variable in scheduler """
	global sched
	sched.turtle2_pose = new_pose

if __name__ == '__main__':
	# create scheduler
	global sched
	sched = TurtleScheduler()
	sched.new(turtle1_wandering(sched))
	sched.new(turtle2_wandering(sched))
	sched.new(cupidon())
	
	# connect to turtlesim
	rospy.init_node('teer_example_turtle')
	# services
	rospy.wait_for_service('reset')
	reset_simulator = rospy.ServiceProxy('reset', EmptyServiceCall)
	reset_simulator()
	rospy.wait_for_service('clear')
	clear_background = rospy.ServiceProxy('clear', EmptyServiceCall)
	spawn_turtle = rospy.ServiceProxy('spawn', Spawn)
	spawn_turtle(0,0,0, "turtle2")
	rospy.wait_for_service('turtle1/set_pen')
	turtle1_set_pen = rospy.ServiceProxy('turtle1/set_pen', SetPen)
	rospy.wait_for_service('turtle1/teleport_absolute')
	turtle1_teleport = rospy.ServiceProxy('turtle1/teleport_absolute', TeleportAbsolute)
	rospy.wait_for_service('turtle2/set_pen')
	turtle2_set_pen = rospy.ServiceProxy('turtle2/set_pen', SetPen)
	rospy.wait_for_service('turtle2/teleport_absolute')
	turtle2_teleport = rospy.ServiceProxy('turtle2/teleport_absolute', TeleportAbsolute)
	# subscriber/publisher
	rospy.Subscriber('turtle1/pose', Pose, turtle1_pose_updated)
	turtle1_velocity = rospy.Publisher('turtle1/command_velocity', Velocity)
	rospy.Subscriber('turtle2/pose', Pose, turtle2_pose_updated)
	turtle2_velocity = rospy.Publisher('turtle2/command_velocity', Velocity)
	
	# setup environment
	turtle1_set_pen(0,0,0,0,1)
	turtle2_set_pen(0,0,0,0,1)
	turtle1_teleport(2,2,0)
	turtle2_teleport(2,9,0)
	clear_background()
	
	# run scheduler
	sched.run()