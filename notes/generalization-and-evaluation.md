# Overfitting and regularization

This is how generalization in machine learning works. Models are fit on a training set and judged on data they did not train on. Overfitting is a low loss on the training set and a much higher loss on new data. The model has memorized accidents in the sample: a particular id, a timestamp, the noise. Underfitting is the opposite. The model is too weak, or training stopped too early, and the loss is high everywhere. The useful region is in between.

Regularization pushes the model away from memorizing. Weight decay adds the size of the parameters to the loss so huge weights are expensive. Dropout randomly hides units during training so the network cannot rely on one path. Early stopping watches a validation loss and keeps the parameters from the point before that loss starts rising. Data augmentation invents extra examples by perturbing inputs in ways that should not change the label, such as a small crop of a photo. More real data beats all of these. A regularizer is not a substitute for a training set that covers the cases you care about.

# Splits and metrics

The training split updates parameters. The validation split is for choices a person makes: architecture, learning rate, when to stop. The test split is touched once, at the end, to estimate how the frozen model behaves on unseen data. If you tune on the test split, it becomes a second validation set and the number you report is optimistic. A random split is right when rows are independent. It is wrong for time series and for users. Split by time, or by user, or the model will train on Monday and be tested on a shuffled Tuesday that leaked into the same day.

Accuracy hides a lot when classes are uneven. A detector that always says "not fraud" is accurate and useless. Precision is the fraction of positive predictions that were right. Recall is the fraction of real positives the model caught. A higher threshold usually raises precision and lowers recall. Pick the threshold from the costs of the two mistakes, on the validation set, and do not retune it after seeing the test set. For regression, look at error in the units of the target, not only at a squared loss that is hard to explain.

# Baselines

A machine learning result means nothing without a baseline. The baseline can be predicting the most common class, predicting the training-set mean, or a short list of rules a person would have written. If a neural network does not beat that, the network is not earning its complexity. Keep the baseline in the same evaluation harness as the model, on the same split, with the same metric. Report the comparison. An improvement of a tenth of a percent that disappears when you change the seed is not an improvement. Run more than one seed when the training noise is large, and say how wide the results were.
