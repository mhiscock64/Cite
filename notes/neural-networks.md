# Layers and activations

This is how a neural network works. A network of this kind is a stack of parameterized functions. A dense layer computes a weighted sum of its inputs, adds a bias, and passes the result through an activation. Without a nonlinearity such as ReLU, a stack of layers would collapse into one linear function, no matter how deep. ReLU keeps positive values and zeroes the rest. It is cheap and is the default in many networks. The last layer matches the task: a single number for regression, a softmax over classes for classification. Softmax turns scores into positive numbers that sum to one, which you can treat as a model's confidence, not as a calibrated probability, unless you have checked the calibration.

Depth lets a network build features in stages. Early layers in an image network respond to edges. Later layers respond to parts and then to objects. No one programs those detectors. They fall out of minimizing the loss, which is why the internal features are only as meaningful as the training signal. Width is the number of units in a layer. A wider layer can represent more patterns at that stage. More parameters need more data, or they memorize.

# Backpropagation

Backpropagation is how a neural network computes the gradient. It is the chain rule, applied from the loss backward through each layer. The forward pass stores the activations. The backward pass multiplies by each layer's local derivative and sends a gradient to the previous layer and to that layer's weights. Automatic differentiation in frameworks such as PyTorch records the operations and plays this backward pass for you. You still choose the architecture, the loss, and the data. Autograd does not choose what is worth learning.

Vanishing gradients happen when many small derivatives multiply and the early layers barely move. Exploding gradients happen when they multiply into huge steps. Careful initialization, residual connections that add a layer's input to its output, and gradient clipping are the usual counters. A residual connection gives the loss a short path, which is why very deep networks became trainable.

# Convolution and sequence models

A convolutional layer reuses one small filter across an image. Sharing the weights means an edge detector learned in one corner works in another, and the parameter count stays small. Pooling or strided convolution shrinks the map so later layers see a wider context. This bias matches images. It is a poor default for a table of unrelated columns.

Sequence models consume ordered inputs. A recurrent network folds a step into a hidden state and carries that state forward. It struggles with long range dependencies because the state is a bottleneck. Attention, described in the note on transformers, lets a step look at any earlier step directly. That is the architecture behind current language models. The neural network is still trained by gradient descent on a loss. Only the wiring changed.
