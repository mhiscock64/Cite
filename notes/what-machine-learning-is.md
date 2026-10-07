# Supervised learning

This is how machine learning works when the examples are labeled. Machine learning learns a task from data instead of from hand-written rules. In supervised learning each example is a pair: an input, and the target the model should produce. The input might be the pixels of a photo, the words of an email, or a row of measurements. The target might be a category, such as spam or not spam, or a number, such as tomorrow's temperature.

The model is a function with adjustable numbers called parameters. Training searches for parameters that make the function's outputs agree with the targets on the examples you have. A classifier picks a class. A regressor predicts a continuous value. The same idea covers both: show inputs and targets, score the disagreement, and adjust the parameters to reduce that score. After training, the model is applied to a new input it did not see. The hope is that the pattern it found in the training examples still holds.

Rules written by a person break when the world is too messy to enumerate. A machine learning model can absorb that mess, but only the mess that was in the data. If the labeled examples never include a kind of input, the model has no reason to handle it well. Supervised learning is only as good as the labels and the coverage of the examples.

# Unsupervised and self-supervised learning

Unsupervised learning has inputs and no targets. Clustering groups similar rows. A dimensionality reduction such as PCA compresses many columns into a few axes that still explain most of the variation. These methods describe structure. They do not, by themselves, know which structure you care about, because you never said what the right answer was.

Self-supervised learning builds the target from the input itself. A language model hides a token and trains the network to predict it, or it trains the network to predict the next token from the ones before it. An image model hides a patch and trains the network to fill it in. No person wrote a label for each example. The task is a pretext, and the useful part is the internal representation the network is forced to learn in order to succeed. Most modern language models are pretrained this way, on huge collections of text, before anyone adapts them to a narrower job.

# Reinforcement learning

Reinforcement learning trains a policy, a rule that maps a situation to an action. There is no labeled correct action. The environment returns a reward, sometimes much later than the action that caused it. The agent tries actions, observes rewards, and shifts the policy toward actions that lead to more reward. Games, robot control, and some stages of language-model training use this pattern. It is harder than supervised learning because the feedback is sparse and the agent can change the data it sees by changing how it acts. A policy that finds a shortcut in the reward, rather than the behavior you actually wanted, is a classic failure. The reward has to match the goal.
