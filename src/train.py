"""
Testing ideas from RL^2 : Fast RL via Slow RL (OpenAI) on a multi armed bandit
"""

import tensorflow as tf
import tensorflow.contrib.slim as slim
import numpy as np
import random
import time
import agent
import gym



def train():
    tf.reset_default_graph()
    #  summary_writer = tf.summary.FileWriter('summaries/perms')

    masses = [0.1, 1]
    lengths = [0.5, 1, 2]
    state_permutations = [
            [0, 1, 2, 3]] #, [2, 3, 0, 1]] #,
            # [0, 1, 3, 2],
            # [0, 2, 1, 3],
            # [0, 2, 3, 1],
            #[0, 3, 1, 2],
            #[0, 3, 2, 1],
            #[1, 0, 2, 3],
            #[1, 0, 3, 2],
            #[1, 2, 0, 3],
            #[1, 2, 3, 0],
            #[1, 3, 0, 2],
            #[1, 3, 2, 0],
            #[2, 0, 1, 3],
            #[2, 0, 3, 1],
            #[2, 1, 0, 3],
            #[3, 0, 1, 2],
            #[3, 0, 2, 1],
            #[3, 1, 0, 2]]

    action_perms = [[0, 1, 2]] #, [2, 1, 0]] #, [0, 2, 1], [1, 0, 2], [2, 1, 0]]
    n_actions = 3
    statesize = 4
    nn = agent.RL2(n_actions, statesize)

    # params
    n_trials = int(10e5)
    n_episodes_per_trial = 2
    max_ep_length = 2000
    GAMMA = 0.97

    env = gym.make('Acrobot-v1')
    env.reset()

    results_file = open('results.txt', 'w', 1)

    with tf.Session() as sess:
        saver = tf.train.Saver(max_to_keep=100)
        init = tf.global_variables_initializer()
        sess.run(init)


        for t in range(n_trials):

            # gravity = random.choice(gravities)
            # length = random.choice(pole_lenghts)
            # env.gravity = gravity
            # env.length = length
            # env.polemass_length = env.masspole*env.length
            l1, l2 = random.choice(lengths), random.choice(lengths)
            m1, m2 = random.choice(masses), random.choice(masses)
            perm = random.choice(state_permutations)
            a_perm = random.choice(action_perms)
            hidden_state = None

            inputs, stateinputs, rewards, values = [], [], [], []
            episode_lengths = []

            trial_rewards = []

            for e in range(n_episodes_per_trial):

                env.reset()
                env.LINK_LENGTH_1 = l1
                env.LINK_LENGTH_2 = l2
                env.LINK_MASS_1 = m1
                env.LINK_MASS_2 = m2
                total_episode_reward = 0

                # taking initial action
                action = random.randint(0, n_actions-1)

                i = 0
                done = False
                while i < max_ep_length and not done:
                    perm_action = a_perm[action]
                    observation, reward, done, info = env.step(perm_action)
                    observation = np.array(observation)[perm]
                    total_episode_reward += reward

                    stateinputs.append(observation)
                    terminated = 1 if done or i == max_ep_length-1 else 0
                    if terminated:
                        reward = 10
                    rnn_input = np.array([action, terminated, reward])
                    inputs.append(rnn_input)
                    rewards.append(reward)

                    feed_dict = { 
                            nn.batch_size : 1,
                            nn.sequence_length: 1,
                            nn.input : [[rnn_input]],
                            nn.state_input: [[observation]],
                    }
                    if hidden_state is not None:
                        feed_dict[nn.initial_state] = hidden_state

                    policy, hidden_state, value = sess.run(
                            [nn.last_actions_distribution, nn.rnn_output_state, nn.value_function], 
                            feed_dict)
                    values.append(value[0][0])

                    # choosing action
                    action = np.random.choice(range(n_actions), p=policy)

                    i += 1

                episode_lengths.append(i)
                trial_rewards.append(total_episode_reward)


            # TRAINING
            value_plus = values + [0]
            advantages = np.array(rewards) + GAMMA * np.array(value_plus[1:]) - np.array(value_plus[:-1])
            advantages = agent.discount(advantages, GAMMA)

            feed_dict={
                nn.batch_size : 1,
                nn.sequence_length : len(inputs),
                nn.input : np.array([inputs]),
                nn.state_input: [stateinputs],
                nn.reward : [agent.discount(rewards, GAMMA)],
                nn.learning_rate : 1e-3,
                nn.advantage : [advantages],
            }
            summary = tf.Summary()

            loss, _, vl, pl, el = sess.run(
                    [nn.loss, nn.train_step, nn.value_loss, nn.policy_loss, nn.entropy],
                    feed_dict)
            print(t, loss, total_episode_reward)
            results_file.write(
                    str(t)+':'+str(l1)+','+str(l2)+':'+str(m1)+','+str(m2)+':'+str(perm)+':'+
                    str([loss, vl, pl, el] + trial_rewards)+'\n')
            #  summary.value.add(tag='Losses/Loss', simple_value=float(loss))
            #  summary.value.add(tag='Losses/ValueLoss', simple_value=float(vl))
            #  summary.value.add(tag='Losses/PolicyLoss', simple_value=float(pl))
            #  summary.value.add(tag='Losses/Entropy', simple_value=float(el))
            #  summary.value.add(tag='Reward/AverageReward', simple_value=average_trial_reward)
            #  summary_writer.add_summary(summary, t)
            #  summary_writer.flush()

            if t % 10000 == 0:
                saver.save(sess, "training/save", global_step=t)
        results_file.close()


if __name__ == "__main__":
    train()
    #  test()
