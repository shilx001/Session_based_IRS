import tensorflow as tf
import numpy as np
import tensorflow.contrib.slim as slim


# Tree Policy with shared parameter nodes

class SharedTreePolicy:
    def __init__(self, state_dim, layer=3, branch=32, hidden_size=64, learning_rate=1e-4, seed=1,
                 stddev=0.03):
        self.state_dim = state_dim
        self.sess = tf.Session()
        self.layer = layer
        self.branch = branch
        self.hidden_size = hidden_size
        self.learning_rate = learning_rate
        self.seed = seed
        self.stddev = stddev
        np.random.seed(self.seed)
        tf.set_random_seed(self.seed)
        self.input_state = tf.placeholder(dtype=tf.float32, shape=[None, state_dim])
        self.input_action = tf.placeholder(dtype=tf.int32, shape=[None, ])
        self.input_reward = tf.placeholder(dtype=tf.float32, shape=[None, ])
        self.output_action_prob = self.forward_pass_v3()
        action_mask = tf.one_hot(self.input_action, self.branch ** self.layer)  # output the action of each node.
        prob_under_policy = tf.reduce_sum(self.output_action_prob * action_mask, axis=1)
        self.loss = -tf.reduce_mean(self.input_reward * tf.log(prob_under_policy + 1e-13), axis=0)
        self.train_step = tf.train.AdamOptimizer(self.learning_rate).minimize(self.loss)
        self.sess.run(tf.global_variables_initializer())

    def mlp(self, id=None, softmax_activation=True):
        '''
        Create a multi-layer neural network as tree node.
        :param id: tree node id
        :param reuse: reuse for the networks
        :return: a multi-layer neural network with output dim equals to branch size.
        '''
        with tf.variable_scope('node_' + str(id), reuse=tf.AUTO_REUSE):
            l1 = slim.fully_connected(self.input_state, self.hidden_size)
            l2 = slim.fully_connected(l1, self.hidden_size)
            l3 = slim.fully_connected(l1, self.branch)
            if softmax_activation:
                outputs = tf.nn.softmax(l3)
            else:
                outputs = l3
        return outputs  # [N, branch]

    def forward_pass(self):
        '''
        Calculate output probability for each item.
        :return: a tensor of the tree policy.
        '''
        node = self.mlp(id='node')
        root_output = node
        for i in range(1, self.layer):  # for each layer
            current_output = []
            for j in range(self.branch ** i):  # for each leaf node
                current_output.append(tf.expand_dims(root_output[:, j], axis=1) * node)
            root_output = tf.concat(current_output, axis=1)  # [N, branch**i], update root_output.
        return root_output

    def forward_pass_v2(self):
        '''
        Calculate output probability for each item, with shared parameter for each layer.
        :return: a tensor of the tree policy.
        '''
        node = [self.mlp(id=str(_)) for _ in range(self.layer)]
        root_output = node[0]
        for i in range(1, self.layer):  # for each layer
            current_output = []
            for j in range(self.branch ** i):  # for each leaf node
                current_output.append(tf.expand_dims(root_output[:, j], axis=1) * node[i])
            root_output = tf.concat(current_output, axis=1)  # [N, branch**i], update root_output.
        return root_output

    def forward_pass_v3(self):
        '''
        Partial shared layer parameter.
        :return: a tensor of the tree policy.
        '''
        node = [self.mlp(id=str(_), softmax_activation=False) for _ in range(self.layer)]
        root_output = node[0]
        for i in range(1, self.layer):  # for each layer
            current_output = []
            for j in range(self.branch ** i):  # for each leaf node
                current_node = slim.fully_connected(node[i], num_outputs=self.branch, activation_fn=tf.nn.relu)
                current_node = slim.fully_connected(current_node, num_outputs=self.branch, activation_fn=tf.nn.softmax)
                current_output.append(tf.expand_dims(root_output[:, j], axis=1) * current_node)
            root_output = tf.concat(current_output, axis=1)  # [N, branch**i], update root_output.
        return root_output

    def forward_pass_v4(self):
        '''
        Calculate output probability for each item. shared policy with
        :return: a tensor of the tree policy.
        '''
        node = self.mlp(id='node', softmax_activation=False)
        root_output = node
        for i in range(1, self.layer):  # for each layer
            current_output = []
            for j in range(self.branch ** i):  # for each leaf node
                current_node = slim.fully_connected(node, num_outputs=self.branch, activation_fn=tf.nn.relu)
                current_node = slim.fully_connected(current_node, num_outputs=self.branch, activation_fn=tf.nn.softmax)
                current_output.append(tf.expand_dims(root_output[:, j], axis=1) * current_node)
            root_output = tf.concat(current_output, axis=1)  # [N, branch**i], update root_output.
        return root_output

    def get_action_prob(self, state):
        '''
        get probability for each action.
        :param state: input state, shape=[N, state_dim].
        :return: the probability for each action.
        '''
        state = np.reshape(state, [-1, self.state_dim])
        return self.sess.run(self.output_action_prob, feed_dict={self.input_state: state})

    def train(self, state, action, reward):
        '''
        Update the gradient of the policy network.
        :param state: input state.
        :param action: input action.
        :param reward: input return.
        :return: the loss value of each update.
        '''
        state = np.reshape(state, [-1, self.state_dim])
        action = np.reshape(action, [-1, ])
        reward = np.reshape(reward, [-1, ])
        loss = self.sess.run(self.loss, feed_dict={self.input_state: state, self.input_action: action,
                                                   self.input_reward: reward})
        self.sess.run(self.train_step, feed_dict={self.input_state: state, self.input_action: action,
                                                  self.input_reward: reward})
        return loss
