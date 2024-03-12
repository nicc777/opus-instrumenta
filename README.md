```text


                     o-o  o--o  o   o  o-o                      
                    o   o |   | |   | |                         
                    |   | O--o  |   |  o-o                      
                    o   o |     |   |     |                     
                     o-o  o      o-o  o--o                      
                                                                
                                                                
o-O-o o   o  o-o  o-O-o o--o  o   o o   o o--o o   o o-O-o   O  
  |   |\  | |       |   |   | |   | |\ /| |    |\  |   |    / \ 
  |   | \ |  o-o    |   O-Oo  |   | | O | O-o  | \ |   |   o---o
  |   |  \|     |   |   |  \  |   | |   | |    |  \|   |   |   |
o-O-o o   o o--o    o   o   o  o-o  o   o o--o o   o   o   o   o
```

Implementation of standard `TaskProcessor` implementations of the [magnum-opus](https://github.com/nicc777/magnum-opus) library.


# Development Quick Start

Preparing your local system for development:

```shell
python3 -m venv venv

. venv/bin/activate

pip3 install -r requirements.txt
```

Also install the latest version of [magnum-opus](https://github.com/nicc777/magnum-opus). For now, assuming you have cloned and build `opus` locally, install the `opus` library from the package in the `dist/` directory from the project directory. An example:

```shell
pip3 install $HOME/git/opus/dist/opus-1.tar.gz
```
