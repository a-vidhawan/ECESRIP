# Hopfield Network: Curated Code Repositories & Datasets

*Compiled for ECE199 SRIP — Last updated: May 2026*

---

## Training & Testing Code — GitHub Repositories

### Classical Hopfield Networks (Python)

| Repo | Stars approx. | Key features | Link |
|------|---------------|--------------|------|
| `takyamamoto/Hopfield-Network` | ★★★ | Both async & sync update; MNIST via `train_mnist.py`; numpy + skimage + keras | [GitHub](https://github.com/takyamamoto/Hopfield-Network) |
| `zftan0709/Hopfield-Network` | ★★ | **Explicitly compares async vs sync** — good for update-order experiments | [GitHub](https://github.com/zftan0709/Hopfield-Network) |
| `duskybomb/hopfield-network` | ★★ | Clean Hebbian learning implementation; minimal deps | [GitHub](https://github.com/duskybomb/hopfield-network) |
| `yosukekatada/Hopfield_network` | ★★ | Pattern memorize → noisy recall; good pedagogical baseline | [GitHub](https://github.com/yosukekatada/Hopfield_network) |
| `felix-andreas/hopfieldnetwork` | ★★ | GUI for visualization; useful for demos | [GitHub](https://github.com/felix-andreas/hopfieldnetwork) |
| `crypto-code/Hopfield-Network` | ★★ | Image reconstruction; train folder → `train.py` → recall | [GitHub](https://github.com/crypto-code/Hopfield-Network) |
| `DenseLance/hopfield-networks` | ★★ | Image restoration + NP-hard combinatorial problems | [GitHub](https://github.com/DenseLance/hopfield-networks) |
| `srowhani/hopfield-network` | ★ | Straightforward educational implementation | [GitHub](https://github.com/srowhani/hopfield-network) |

### MNIST-Specific Implementations

| Repo | Description | Link |
|------|-------------|------|
| `kencyke/hopfield-mnist` | Hopfield network trained on MNIST digits | [GitHub](https://github.com/kencyke/hopfield-mnist) |
| `grinvolod13/mnist-hopfield` | MNIST classification via Hopfield | [GitHub](https://github.com/grinvolod13/mnist-hopfield) |
| `mballarin97/Hopfield-project` | MNIST analysis, both deterministic & stochastic (physical/Boltzmann) approach | [GitHub](https://github.com/mballarin97/Hopfield-project) |

### Modern Hopfield Networks (Dense Associative Memory / Attention)

| Repo | Description | Link |
|------|-------------|------|
| `ml-jku/hopfield-layers` | **"Hopfield Networks is All You Need"** official implementation (PyTorch 1.6+); Hopfield layers as drop-in attention modules | [GitHub](https://github.com/ml-jku/hopfield-layers) |
| `hmcalister/Hopfield-Network-PyTorch` | PyTorch + CUDA for speed; good for large-N experiments | [GitHub](https://github.com/hmcalister/Hopfield-Network-PyTorch) |

### Hardware / FPGA Relevant

- **Architecture Analysis of an FPGA-Based Hopfield Neural Network** — uses registers, weight ROMs (LUTs), multipliers, adders; modified arch reduces area 87.5%, timing 3×. [Academia.edu](https://www.academia.edu/33481965/Architecture_Analysis_of_an_FPGA_Based_Hopfield_Neural_Network)
- **Fault-Tolerant Hopfield on FPGAs** — ResearchGate paper on redundancy strategies. [ResearchGate](https://www.researchgate.net/publication/304261665_Hardware_implementation_of_a_fault-tolerant_Hopfield_Neural_Network_on_FPGAs)
- **Fractional-Order Hopfield on FPGA (2026)** — Grünwald-Letnikov calculus + Chebyshev piecewise linear approx for activation. [ADS Abstract](https://ui.adsabs.harvard.edu/abs/2026ITCSR..73.1174M/abstract)
- **SRAM-based FPGA Hopfield** — O(1) multiplications, O(log N) additions (vs O(N)/O(N) standard). Springer. [Springer](https://link.springer.com/chapter/10.1007/11494669_71)

---

## Datasets

### Standard Benchmarks for Hopfield Experiments

#### 1. Binary MNIST
- **What**: 70,000 handwritten digit images (28×28), binarized to ±1
- **Use**: Store 10 prototype digit patterns; test noisy recall
- **How to get**: `torchvision.datasets.MNIST` or `sklearn.datasets.fetch_openml('mnist_784')`
- **Encoding**: pixel > 128 → +1, else −1
- **Repos using it**: `takyamamoto`, `kencyke`, `grinvolod13`, `mballarin97`

#### 2. Fashion MNIST
- **What**: 70,000 clothing images (28×28), 10 classes
- **Use**: Harder patterns than digits; tests capacity limits
- **How to get**: `torchvision.datasets.FashionMNIST`
- **Note**: Some repos achieve 100% recall on 5-pattern subsets with sync update

#### 3. Synthetic Binary Patterns (Random ±1 Vectors)
- **What**: Randomly generated ±1 vectors of length N
- **Use**: Capacity analysis (Hopfield capacity ≈ 0.138N for Hebbian); spurious state counting
- **How to generate**: `np.random.choice([-1, 1], size=(P, N))`
- **Key metric**: % of patterns correctly recalled as function of P/N ratio

#### 4. UCI Machine Learning Repository (small tabular)
- **What**: Collection of small classification datasets
- **Use**: Used in "Hopfield Networks is All You Need" to benchmark Hopfield layers vs. GBM/RF/SVM
- **How to get**: `https://archive.ics.uci.edu/ml/datasets.php`

#### 5. MS-COCO (for Modern Hopfield / Dense Associative Memory)
- **What**: 110,000 images with captions
- **Use**: High-dimensional realistic distribution; tests modern Hopfield retrieval at scale
- **How to get**: `https://cocodataset.org/#download`

#### 6. Custom Binary Image Patterns
- **What**: Small hand-crafted binary images (letters, symbols, faces)
- **Use**: Classic demos; visually interpretable recall
- **How to generate**: Draw in any image editor, convert to ±1

### Dataset Quick-Start (Python Snippet)

```python
import numpy as np
from sklearn.datasets import fetch_openml

# Binary MNIST (binarized)
mnist = fetch_openml('mnist_784', version=1, as_frame=False)
X = np.where(mnist.data > 128, 1, -1)   # shape: (70000, 784)
y = mnist.target.astype(int)

# Extract one prototype per digit class
prototypes = np.array([X[y == i].mean(axis=0) for i in range(10)])
prototypes = np.sign(prototypes)         # shape: (10, 784)

# Synthetic patterns for capacity testing
N, P = 100, 10
patterns = np.random.choice([-1, 1], size=(P, N))
```

---

## Key Papers to Read

| Paper | Year | Why relevant |
|-------|------|--------------|
| Hopfield, J.J. — "Neural networks and physical systems with emergent collective computational abilities" | 1982 | The original; defines energy function and async convergence proof |
| Hopfield, J.J. — "Neurons with graded response have collective computational properties" | 1984 | Continuous-valued extension |
| Amit, Gutfreund & Sompolinsky — "Statistical mechanics of neural networks near saturation" | 1987 | Capacity analysis (0.138N result) |
| Ramsauer et al. — "Hopfield Networks is All You Need" (arXiv:2008.02217) | 2020 | Modern Hopfield; exponential capacity; connection to attention |
| Krotov & Hopfield — "Dense Associative Memory for Pattern Recognition" | 2016 | Bridge between classical and modern |
| "Synchronous vs asynchronous behavior of Hopfield's CAM neural net" | 1987 | Key paper specifically on update order effects |
| "On the Dynamics of a Recurrent Hopfield Network" (arXiv:1502.02444) | 2015 | Dynamics, limit cycles, energy analysis |
