"""# Plaque Demo

with plaque, you just write ordinary python in *your own* editor.

This can then be converted into a nice looking HTML rendering, with $\LaTeX$ support."""

import numpy as np
import matplotlib.pyplot as plt

# %%


def sinc(x):
    return np.sin(x) / x


""" You can insert [markdown](https://en.wikipedia.org/wiki/Markdown) cells as top level comments """

xs = np.linspace(0, 10, 300)
plt.plot(xs, np.sin(xs) / xs)
plt.title("Example figure")
plt.xlabel("$x$")
plt.ylabel(r"$\sin(x)/x$")
plt.show()
