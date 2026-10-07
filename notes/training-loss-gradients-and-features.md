# Loss and gradient descent

This is how training a machine learning model works. Training minimizes a loss. The loss is a single number that says how wrong the model's predictions are on a batch of examples. For classification, cross-entropy punishes confident wrong answers more than uncertain ones. For regression, squared error punishes large misses more than small ones. The training algorithm does not understand the task. It only sees this number and the parameters that produced it.

Gradient descent changes each parameter a little in the direction that reduces the loss. The gradient is the vector of partial derivatives of the loss with respect to every parameter. Stepping against the gradient is the steepest local decrease. The learning rate is the size of that step. Too large, and the loss jumps around or diverges. Too small, and training is slow and can stall in a flat region. Stochastic gradient descent does not compute the gradient on the entire dataset. It uses a minibatch, a small random subset, which is noisier but far cheaper and often generalizes better.

An epoch is one pass over the training set. Batches tile an epoch. Shuffling each epoch stops the model from learning the order of the file. Optimizers such as Adam keep a running estimate of the gradient and its square so each parameter gets an adapted step size. They are still gradient descent. They do not change what the loss means.

# Features, labels, and leakage

A feature is a number the model is allowed to see. A label is the target it must predict. The split between them is a design choice, and it is the most common place machine learning projects go wrong. If a feature is a copy of the label, or is computed from the label, or is only known after the outcome, the model looks brilliant in testing and fails in production. That is leakage. Fitting a scaler or a vocabulary on the full dataset before the split is leakage too, because information from the held-out rows influenced the transform.

Build features only from what will be available at prediction time. Fit every statistic, including means, vocabularies, and encodings, on the training split alone, then apply that frozen transform to validation and test. Categorical values the training set never saw need an explicit unknown bucket. Missing values need a policy, not a silent drop of the hard rows, or the model never learns that those rows exist.
