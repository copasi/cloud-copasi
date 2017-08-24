# Introduction


Cloud-COPASI is a web-based tool for running computationally intensive simulation and analysis tasks in parallel on a high-throughput computing pool. Cloud-COPASI can connect to existing computing pools, or provides a simple interface for launching a new computing pool using the [Amazon Elastic Compute Cloud (EC2)](http://aws.amazon.com).

Cloud-COPASI can run a number of simulation and analysis tasks, including global sensitivity analyses, stochastic simulations, parameter scans, optimizations, and parameter fitting. Each task is automatically slit into a number of smaller jobs, which are executed in parallel, allowing for significant speed-ups in running time.

Models must be prepared using [COPASI](http://www.copasi.org) (COmplex PAthway SImulator), a widely used free, open-source, cross-platform simulation tool.

# Usage
We host an implementation of Cloud-COPASI, which is available for use free of charge, at [cloud.copasi.org](http://cloud.copasi.org). For new users this is the recommended option.

### Deployment
For users wishing to deploy their own implementation of Cloud-COPASI, please see the [Deployment Guide](https://github.com/copasi/cloud-copasi/wiki/Deployment). This option is recommended for advanced users only.

# About
Cloud-COPASI was developed by Edward Kent in the [Computational Systems Biology and Biochemical Networks Modeling Group](http://www.comp-sys-bio.org) at the [University of Manchester](http://www.manchester.ac.uk), UK, and is built on the [Condor-COPASI](https://github.com/copasi/condor-copasi) software. Cloud-COPASI is written in Python using the Django web application framework. [Bosco](http://bosco.opensciencegrid.org/) is used to connect to remote compute pools, and [HTCondor](http://research.cs.wisc.edu/htcondor/) is used to manage job allocation on EC2 pools.

# License
    The files in the /html5up/ directory contain the ZeroFour HTML template
    package provided by HTML5 Up!. These files are released under the CCA 3.0
    license (/html5up/LICENSE.txt)
    
    All other files, unless otherwise stated, are released under the GNU GENERAL
    PUBLIC LICENSE Version 3 (/LICENSE.txt)
    
    They are distributed in the hope that they will be useful
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
