# -*- coding: utf-8 -*-
"""Imageclassification_NN_Dropout.ipynb

We will take a look at simple but effective methods used to combat overfitting when learning neural networks. 
We will use a very small subset of the FashionMNIST dataset to artificially induce overfitting, train and evaluate our model. 
Finally we will look at how to incorporate early stopping and how adding noise to our data makes our model more robust.
"""

from typing import Callable
from functools import partial

import torch
from torch import nn
from torch.optim import Optimizer, SGD

from torchvision.transforms import v2

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

import torch
from torch import nn
from torch.nn.functional import cross_entropy
from torch.utils.data import DataLoader

from itertools import product
from typing import Callable

import matplotlib.pyplot as plt

from torchvision.datasets import FashionMNIST
from torch.utils.data import random_split, DataLoader

def get_fashion_mnist_subset(n_train_samples: int, n_val_samples: int, transforms: Callable) -> tuple[DataLoader, DataLoader]:
    full_train_set = FashionMNIST("sample_data", train=True, download=True, transform=transforms)
    train_set, val_set, _ = random_split(full_train_set,
        [n_train_samples, n_val_samples, int(6e4) - (n_train_samples + n_val_samples)])

    test_set = FashionMNIST("sample_data", train=False, download=True, transform=transforms)

    return train_set, val_set, test_set


def visualize_first_4(dataloader):
    for batch, labels in dataloader:
        break

    print(f"Shape of images is {batch.shape}")
    fig, axs = plt.subplots(2, 2)
    for i, j in product((0, 1), (0, 1)):
        axs[i, j].imshow(batch[2*i + j][0])
        axs[i, j].set_title(f"Label: {labels[2*i + j]}")
        axs[i, j].tick_params(left = False, right = False , labelleft = False ,
                labelbottom = False, bottom = False)
    plt.show()


def plot_train_and_val_loss(train_l, val_l, title=""):
    plt.clf()
    plt.plot(train_l, label="Train loss")
    plt.plot(val_l, label="Validation loss")
    plt.axhline(y=min(val_l), c="r", linestyle="--")
    plt.legend(loc="upper right")
    plt.title(title)
    plt.show()

"""# Training configuration
"""

TRAIN_SET_SIZE = 200
VAL_SET_SIZE = 1000
EPOCHS = 500
HIDDEN_DIMS = [64, 32]
LR = 0.05
BATCH_SIZE = 32

"""# Dataset (FashionMNIST)

As mentioned before, we will use the FashionMNIST dataset. This dataset behaves exactly the same as the standard MNIST dataset (grayscale images with height and width of 28 pixels, 
10 classes (0-9), train set with 60k samples and test set with 10k samples) with the only difference being the depicted images. 
While MNIST shows handwritten digits, FashionMNIST shows 10 different types of clothing. Example images are shown after execution of the following cell.
"""

train_set, val_set, test_set = get_fashion_mnist_subset(TRAIN_SET_SIZE, VAL_SET_SIZE, transforms=v2.ToTensor())

train_loader = DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True)
val_loader = DataLoader(val_set, batch_size=BATCH_SIZE)
test_loader = DataLoader(test_set, batch_size=BATCH_SIZE)

visualize_first_4(train_loader)

"""# Create model

First, we need a function to create a model that is able to classify FashionMNIST data. 
The model takes in inputs of the shape (batch_size x 1 x 28 x 28) and outputs a 10-dimensional vector. 
It should first flatten the input images, then apply a given number of linear layers to it, and finally map to a 10-dimensional vector which will be used to predict which type of clothing it is.

"""

def create_model(hidden_dims: list[int]):  #
    """Create a model that works for classifying the FahsionMNIST dataset."""
    # --------------------------------------------------
    model = nn.Sequential(
        nn.Flatten(),
        nn.Linear(28*28, hidden_dims[0]),
        nn.ReLU(),
        *[nn.Sequential(nn.Linear(in_feats, out_feats), nn.ReLU())
            for in_feats, out_feats in zip(hidden_dims[:-1], hidden_dims[1:])],
        nn.Linear(hidden_dims[-1], 10)
    )

    model.to(DEVICE)
    return model

"""# Train, evaluate and save models

## 
Write a function that trains a model for one epoch / one iteration through the train dataset.
"""

def train_one_epoch(model, dataloader, optimizer):
    # --------------------------------------------------
    losses = []
    for batch, labels in dataloader:
        batch = batch.to(DEVICE)
        labels = labels.to(DEVICE)

        optimizer.zero_grad()

        preds = model(batch)
        loss = cross_entropy(preds, labels)
        loss.backward()
        optimizer.step()

        losses.append(loss.item())

    avg_loss = sum(losses) / len(losses)
    return avg_loss

"""

Write a function that iterates through a dataloader, and outputs the average loss and accuracy. 
"""

def validate(model: nn.Module, dataloader: DataLoader) -> tuple[float, float]:
    losses = []
    accuracies = []

    model.eval()

    with torch.no_grad():
        for batch, labels in dataloader:
            batch = batch.to(DEVICE)
            labels = labels.to(DEVICE)

            preds = model(batch)

            loss = cross_entropy(preds, labels)
            losses.append(loss.item())

            accuracy = torch.sum(torch.argmax(preds, dim=-1) == labels)
            accuracies.append(accuracy.item() / len(labels))

    model.train()

    avg_loss = sum(losses) / len(losses)
    avg_acc = sum(accuracies) / len(accuracies)

    return avg_loss, avg_acc

"""Here we define our complete training function. It simply iterates for `n_epochs` epochs through the training dataset, evaluates after each epoch on the validation dataset, and finally returns an array with the train and validation losses for each epoch. An important feature of this training function is that it can take a function as an argument (that's the `callback` argument) which gets the model, the current epoch, the array of train losses up until this point, the array of validation losses until this point and the last validation accuracy. The follwing tasks will partly consist of writing functions that we will pass into the training function."""

def train(
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        optimizer: Optimizer,
        n_epochs: int,
        callback: Callable[[nn.Module, int, list[float], list[float], float], None]
    ) -> tuple[list[float], list[float]]:
    train_losses = []
    val_losses = []
    for epoch in range(n_epochs):
        train_loss = train_one_epoch(model, train_loader, optimizer)
        val_loss, val_acc = validate(model, val_loader)

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        callback(model, epoch, train_losses, val_losses, val_acc)

    return train_losses, val_losses

"""## 

Write a function that we can pass into the training function above that prints the current stats every `n` epochs. This function shouldn't return anything.
"""

def print_loss_every_n_epochs(
        model: nn.Module,
        epoch: int,
        train_losses: list[float],
        val_losses: list[float],
        val_acc,
        n: int) -> None:
    if epoch % n == 0:
        print(f"[EPOCH {epoch}] Train loss: {train_losses[-1]:.4f}, Validation loss: {val_losses[-1]:.4f}, Validation accuracy: {val_acc:.4f}")

"""Next we will train a model. We will use the above defined hyperparameters, and a simple SGD optimizer. Furthermore we will print the training stats every epoch."""

model = create_model(HIDDEN_DIMS)
optimizer = SGD(model.parameters(), lr=LR)

train_losses , val_losses = train(model,
                                   train_loader,
                                   val_loader,
                                   optimizer,
                                   n_epochs=10,
                                   callback=partial(print_loss_every_n_epochs, n=1))

plot_train_and_val_loss(train_losses, val_losses, title=f"min. validation loss: {min(val_losses):.4f}")

"""# Early stopping ## """

def save_model_if_improved(model, epoch, train_losses, val_losses, val_acc, filename):
    # --------------------------------------------------
    if val_losses[-1] == min(val_losses):
        print(f"Found new best model at epoch {epoch} with a validation loss of {val_losses[-1]:.4f}")
        torch.save(model.state_dict(), filename)
def load_model(model, model_file_path: str) -> nn.Module:
    model.load_state_dict(torch.load(model_file_path, weights_only=True))
    return model

"""This time we will train our model for more epochs, to show how it overfits. Your implemented function should stop saving the model once the model starts to overfit."""

model = create_model(HIDDEN_DIMS)
optimizer = SGD(model.parameters(), lr=LR)
train_losses, val_losses = train(model,
                                train_loader,
                                val_loader,
                                optimizer,
                                n_epochs=EPOCHS,
                                callback=partial(save_model_if_improved, filename="early_stopping.pth"))

plot_train_and_val_loss(train_losses, val_losses, title=f"min. validation loss: {min(val_losses):.4f}")

"""We now evaluate our model on the test set, to get a better estimate of the generalization error. As you can see we've named the model"""

pretrained_model = create_model(HIDDEN_DIMS)
load_model(pretrained_model, model_file_path="early_stopping.pth")
test_loss, test_accuracy = validate(pretrained_model, test_loader)

print(f"Early stopping model achieved test loss of {test_loss:.4f} and accuracy {test_accuracy:.4f}")

"""# Dropout

## 

Implement a function similar to the one above where we build a standard feed forward network. 
But now, after each activation layer, add a [nn.Dropout()layer with the dropout probability specified in the parameter `p`.
"""

def create_model_with_dropout(hidden_dims: list[int], p: float):
    model = nn.Sequential(
        nn.Flatten(),
        nn.Linear(28*28, hidden_dims[0]),
        nn.ReLU(),
        nn.Dropout(p),
        *[nn.Sequential(nn.Linear(in_feats, out_feats), nn.ReLU(), nn.Dropout(p))
            for in_feats, out_feats in zip(hidden_dims[:-1], hidden_dims[1:])],
        nn.Linear(hidden_dims[-1], 10)
    )
    return model

   # model.to(DEVICE)

"""Next we will train a neural network with the exact same parameters as above, only that we now have added dropout layers."""

DROPOUT = 0.8

model = create_model_with_dropout(HIDDEN_DIMS, p=DROPOUT)
optimizer = SGD(model.parameters(), lr=LR)

train_losses, val_losses = train(model,
                                train_loader,
                                val_loader,
                                optimizer,
                                n_epochs=EPOCHS,
                                callback=partial(save_model_if_improved, filename="dropout.pth"))

plot_train_and_val_loss(train_losses, val_losses, title=f"min. validation loss: {min(val_losses):.4f}")

DEVICE

pretrained_model = create_model_with_dropout(HIDDEN_DIMS, DROPOUT)
load_model(pretrained_model, "dropout.pth")
test_loss, test_accuracy = validate(pretrained_model, test_loader)

print(f"Dropout model achieved test loss of {test_loss:.4f} and accuracy of {test_accuracy:.4f}")
