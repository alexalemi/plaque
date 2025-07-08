import matplotlib.pyplot as plt
import numpy as np

# %% [markdown] key=value
# # This is a test
#
# Let's test this notebook thing, see how it works.
# But then if you update the file and save.
# $$ E = mc^2 $$


def square(x):
    return x * x * x


""" You can put some markdown here. If I come over here and edit. I can edit this like *this* """

square(25)


# %%

xs = np.linspace(0, 10, 300)

# %%

plt.plot(xs, np.sin(xs))
plt.plot(xs, np.cos(xs))
plt.show()


""" This is an **extra** *special* test. Markdown is *unique*  """

x = 1 * 3

""" What now? Huh? """

square(1 + 2)


"""Do
single quotes work as well?
"""

""" Yes they do. """

import pandas as pd

# Create a dictionary to hold the data
data = {
    "Name": ["Alice", "Bob", "Charlie", "David"],
    "Age": [25, 30, 35, 28],
    "City": ["New York", "London", "Paris", "Tokyo"],
}

# Create a DataFrame from the dictionary
df = pd.DataFrame(data)

df

# %%

# Testing errors
1 / 0
