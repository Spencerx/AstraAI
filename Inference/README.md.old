# How to run inference?

1. Enter the Mistral environment created using the steps mentioned in the [README section](https://github.com/AIModCon/modcon-hpc/tree/main?tab=readme-ov-file#mistral-environment-setup-on-linux)
```
source <path-to-mistral-env>/bin/activate
```

2. A prompt should be given in a text file `prompt.txt`. An example is 
```
Can you write an AMReX code that demonstrates the creation of a MultiFab and writes a plotfile with this multifab in it?
```
3. Get a GPU interactive node  

4. Run the inference as 
```
python3 inference.py
```

5. The output is written into a file `output.txt`. The above prompt gave the following output -

```
Can you write an AMReX code that demonstrates the creation of a MultiFab and writes a plotfile with this multifab in it?

Yes, here's an example AMReX code that demonstrates the creation of a MultiFab and writes a plotfile with this multifab in it. This example assumes you have a simple scalar field `A` defined on a given BoxArray `grid`.

```cpp
#include <AMReX.H>

int main(int argc, char* argv[])
{
    // Initialize AMReX
    amrex::Initialize(argc, argv);

    // Define BoxArray and Grid
    const int nx = 32;
    const int ny = 16;
    const int nz = 16;
    BoxArray ba(BlkDim(nx, ny, nz));
    Geometry geom(amrex::Edges(nx, ny, nz), amrex::IntVect(0, 0, 0),
                  amrex::IntVect(nx-1, ny-1, nz-1), nx, ny, nz);

    // Create MultiFab for scalar field A
    MultiFab A("A", ba, 1, MFInfo(), MFType::REAL);

    // Set initial values for scalar field A
    for (MFIter mfi(A); mfi.isValid(); ++mfi) {
        const auto& fab = A[mfi];
        const Box& bx = mfi.box();
        for (int i = 0; i < AMREX_SPACEDIM; ++i) {
            for (int j = 0; j < AMREX_SPACEDIM; ++j) {
                for (int k = 0; k < AMREX_SPACEDIM; ++k) {
                    fab(i, j, k) = 1.0;
                }
            }
        }
    }

    // Write plotfile for scalar field A
    ParallelFile pf("output.pots", "write", MPI_COMM_WORLD);
    if (pf.isOpen()) {
        pf << "Field A" << std::endl;
        pf << "Zone (" << ba.numPts() << ")" << std::endl;
        pf << "Data format: AMR" << std::endl;
        pf << "Data type: Real" << std::endl;
        pf << "Coordinates format: Cartesian" << std::endl;
        pf << "Coordinates:" << std::endl;
        pf << "x y z" << std::endl;
        for (MFIter mfi(A); mfi.isValid(); ++mfi) {
            const auto& fab = A[mfi];
            const Box& bx = mfi.box();
            for (int i = 0; i < bx.size(); ++i) {
                const int idx = bx.index3d(i);
                const Real x = geom[0].x(idx);
                const Real y = geom[1].x(idx);
                const Real z = geom[2].x(idx);
                pf << x << " " << y << " " << z << std::endl;
                pf << fab(i) << std::endl;
            }
        }
        pf.close();
    }

    // Clean up AMReX
    amrex::Finalize();
}

This code initializes AMReX, creates a MultiFab for a scalar field `A` on a given BoxArray `ba`, sets 
initial values for `A`, and writes a plotfile `output.pots` with the scalar field data. 
The plotfile format is Potsdam format (`.pots`).
```
