import rclpy
from rclpy.node import Node
from core.cognitive_node import CognitiveNode
import random
import numpy

from std_msgs.msg import Int64
from core.service_client import ServiceClient, ServiceClientAsync
from cognitive_node_interfaces.srv import SetActivation, Execute
from cognitive_node_interfaces.srv import GetActivation

from core.utils import perception_dict_to_msg, class_from_classname

class Policy(CognitiveNode):
    """
    Policy class.
    """
    def __init__(self, name='policy', class_name='cognitive_nodes.policy.Policy', publisher_msg = None, publisher_topic = None, **params):
        """
        Constructor for the Policy class.

        Initializes a policy with the given name and registers it in the LTM.
        It also creates a service for executing the policy.

        :param name: The name of the policy.
        :type name: str
        :param class_name: The name of the Policy class
        :type class_name: str
        :param publisher_msg: The publisher message to publicate the execution of the policy
        :type publisher: str
        :param publisher_topic: The publisher topic to publicate the execution of the policy
        :type publisher: str
        """
        
        super().__init__(name, 'cognitive_nodes.policy.Policy', **params)

        self.set_activation_service = self.create_service(
            SetActivation,
            'policy/' + str(name) + '/set_activation',
            self.set_activation_callback,
            callback_group=self.cbgroup_server
        )

        self.execute_service = self.create_service(
            Execute,
            'policy/' + str(name) + '/execute',
            self.execute_callback,
            callback_group=self.cbgroup_server
        )

        self.publisher_msg = publisher_msg
        self.publisher = self.create_publisher(class_from_classname(publisher_msg), publisher_topic, 0)         

    async def calculate_activation(self, perception):
        """
        Calculate the activation level of the policy by obtaining that of its neighboring CNodes
        As in CNodes, an arbitrary perception can be propagated, calculating the final policy activation for that perception.

        :param perception: Arbitrary perception
        :type perception: dict
        :return: The activation of the Policy
        :rtype: float
        """
        cnodes = [neighbor["name"] for neighbor in self.neighbors if neighbor["node_type"] == "CNode"]
        if cnodes:
            cnode_activations = []
            for cnode in cnodes:
                service_name = 'cognitive_node/' + str(cnode) + '/get_activation'
                activation_client = ServiceClientAsync(self, GetActivation, service_name, self.cbgroup_client)
                perception = perception_dict_to_msg(perception)
                activation = await activation_client.send_request_async(perception = perception)
                cnode_activations.append(activation.activation)
                self.activation = numpy.max(cnode_activations)
        else:
            self.activation = 0.0
        
        self.get_logger().info(self.node_type + " activation for " + self.name + " = " + str(self.activation))
        if self.activation_topic:
            self.publish_activation(self.activation)
        return self.activation
    
    def execute_callback(self, request, response):

        """
        Mock method that pretends to execute the policy.
        It logs the execution and returns the policy name in the response.

        :param request: The request to execute the policy.
        :type request: cognitive_node_interfaces.srv.ExecutePolicy_Request
        :param response: The response indicating the executed policy.
        :type response: cognitive_node_interfaces.srv.ExecutePolicy_Response
        :return: The response with the executed policy name.
        :rtype: cognitive_node_interfaces.srv.ExecutePolicy_Response
        """
        self.get_logger().info('Executing policy: ' + self.name + '...')
        msg = class_from_classname(self.publisher_msg)()
        msg.data = self.name
        self.publisher.publish(msg)
        response.policy = self.name
        return response
    
    def set_activation_callback(self, request, response):
        """
        CNodes can modify a policy's activation

        :param request: The request that contains the new activation value
        :type request: cognitive_node_interfaces.srv.SetActivation_Request
        :param response: The response indicating if the activation was set
        :type response: cognitive_node_interfaces.srv.SetActivation_Response
        :return: The response indicating if the activation was set
        :rtype: cognitive_node_interfaces.srv.SetActivation_Response
        """

        activation = request.activation
        self.get_logger().info('Setting activation ' + str(activation) + '...')
        self.activation = activation
        response.set = True
        return response


def main(args=None):
    rclpy.init(args=args)

    policy = Policy()

    rclpy.spin(policy)

    policy.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()