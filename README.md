# LinAlgebraX

## Video Demo

![LinAlgebraX preview](assets/demo.gif)

[Watch the full demo on YouTube](https://youtu.be/RQzOT0Xk3C8)

#### Description

LinAlgebraX is an interactive linear algebra program written in Python. It allows users to define their own vectors, matrices, vector families, linear systems, and polynomials directly in the terminal to perform computations on them, and observe the corresponding transformations in a separate animated window.

Unlike a fixed collection of demonstrations, LinAlgebraX works with objects entered by the user. A matrix can be defined once, stored under a name, and then reused in commands such as `inverse A`, `noyau A`, or `spectre A`. The program therefore acts both as a command-line calculator and as a visual exploration tool.

The main goal is the direct manipulation of mathematical objects, exact computation, and visual representations generated from real commands, a laboratory for linear Algebra.

## Main Features

The program allows the user to define :

* vectors
* matrices
* vector families
* linear systems
* polynomials

It implements several topics from introductory and MP2I(first year of French Preparatory Program for Grandes Écoles) level linear algebra, including:

* Gauss-Jordan elimination
* matrix rank
* determinants
* matrix inversion
* kernels and images
* linear system solving
* linearly independent and spanning families
* bases and coordinates
* sums and intersections of subspaces
* complementary subspaces
* Gram-Schmidt orthogonalization
* orthogonal projections
* orthogonal symmetries
* change-of-basis matrices
* dot and cross products
* Cramer's rule
* isomorphisms and automorphisms
* real eigenvalues and eigenvectors of (2 \times 2) matrices
* polynomial evaluation, differentiation, and integration

Objects entered through the terminal may have dimensions from 1 to 5 and general matrix operations work throughout this range. The explicit eigenvalue computation is intentionally limited to real (2 \times 2) matrices because exact symbolic root finding in higher dimensions would require a much larger computer algebra system.

## Exact Arithmetic

I use Python's `Fraction` class for rational calculations. This is especially useful for Gauss-Jordan elimination, determinants, kernels, and linear systems, where small floating-point errors could otherwise produce false results.


## Installation

On Ubuntu or Debian install the required system packages:

```bash
sudo apt install python3-venv python3-tk
```

Then make the launcher executable and run it

```bash
chmod +x lancer.sh
./lancer.sh
```

The launcher creates a local `.venv` virtual environment and installs the packages listed in `requirements.txt`, it does not modify the system-wide Python installation.

but the project can also be started manually

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 project.py
```

## Example Session

The commands are written in french (because i'm French) but their structure is intentionally simple.

First, define some mathematical objects:

```text
A = [[2, 1], [1, 2]]
v = (3, 2)
F = [(1, 1)]
S = {2x + y = 5 ; x + 2y = 4}
P = X^3 - 2X + 1
```

These objects are stored in the current session and can then be used by name:

```text
etudier A
det A
inverse A
noyau A
image A
resoudre S
projection v ; F
spectre A
derivee P
```

For example:

```text
inverse A
```

retrieves the matrix stored under the name `A`, applies Gauss-Jordan elimination to the augmented matrix ([A \mid I]), extracts the inverse, records the elementary row operations, prepares a textual and LaTeX representation, and sends the corresponding animation to the visualization window.

Use:

```text
commandes
```

to display the complete command list.

## Session Management

The program keeps its state while it is running.

```text
memoire
```

displays the currently defined objects and the recent command history.

```text
supprimer A
```

removes the object named `A`.

```text
supprimer tout
```

clears all stored objects.
```text
retour
```

undoes the most recent action. The program restores both the previous mathematical state and the previous visualization state.
The undo system stores a snapshot before each meaningful action.

## Project Structure

`project.py` is the official entry point required by CS50P. It contains `main` and three additional functions that can be tested independently:

* `lire_commande`
* `executer_commande`
* `afficher_reponse`

Its responsibility is limited to the terminal interface and the main application loop. It reads a command, passes it to the session engine, displays the returned response, and forwards the optional scene data to the visualization window.

`moteur.py` is the command and session engine. It recognizes commands, retrieves the required objects, calls the appropriate mathematical functions, builds responses, and manages the object memory, history, and undo mechanism.

`analyseur.py` converts textual input into mathematical objects. It recognizes vectors, matrices, vector families, and linear systems. It uses Python's `ast` module instead of `eval`, allowing the program to accept structured expressions without directly executing arbitrary user input

`algebre.py` contains the mathematical core. It defines the `Vecteur` and `Matrice` classes and implements the main linear algebra algorithms. This module does not read from the terminal and does not depend on the graphical window.

`polynomes.py` defines the `Polynome` class. A polynomial is represented by its coefficients, similarly to the coordinate representation of a vector. The module implements addition, subtraction, multiplication, powers, evaluation, differentiation, and integration

`presentation.py` converts calculated objects into terminal text and LaTeX strings. It does not perform the mathematical calculations again. This separation allows the same result to be displayed in different forms without changing the algorithms.

`test_project.py` contains the tests required by CS50P and additional tests for the mathematical core, command engine, session memory, undo behavior, scene generation, animation controls, LaTeX output, and camera movement.


The visualisation/ directory contains the complete graphical subsystem. It is kept separate from the mathematical core so that matrix and vector calculations do not depend on Tkinter, animations, or graphical rendering.
`visualisation/creation_scenes.py` converts mathematical objects and calculation results into scene descriptions.
`visualisation/liaison_observatoire.py` starts the visualization window and sends scene data to it.
`visualisation/fenetre_observatoire.py` draws the scenes, renders animations, manages the timeline, and controls the three-dimensional camera.
`visualisation/__init__.py` marks the directory as a Python package.

`requirements.txt` lists the external Python packages required to run and test the project.

`lancer.sh` creates the virtual environment, installs the dependencies, and starts the application on Linux


## Command Execution Flow

For exemple, for the command `inverse A`:

1. `project.py` reads the input line.
2. `Laboratoire.executer` in `moteur.py` recognizes the command.
3. `Matrice.inverse` in `algebre.py` computes the exact result.
4. `presentation.py` prepares the readable text and LaTeX output.
5. `creation_scenes.py` prepares the animation data.
6. `liaison_observatoire.py` sends the data to the observatory.
7. `fenetre_observatoire.py` renders the animation.



## Testing

Run the complete test suite with:

```bash
pytest
```

The tests cover:

* the three required functions in `project.py`
* vector and matrix construction
* exact matrix operations
* Gauss-Jordan elimination
* determinants and inverses
* kernels and images
* unique, infinite, and inconsistent linear systems
* vector families and linear dependence
* Gram-Schmidt orthogonalization
* projections
* polynomial operations
* sums and intersections of subspaces
* session memory and object deletion
* the undo system
* the dimension limit
* scene generation
* the `PLAY` animation control
* LaTeX output
* three-dimensional camera movement

The mathematical tests generally verify mathematical identities rather than only comparing printed output. For example, the inverse test verifies that

```python
A @ inverse == Matrice.identite(2)
```
