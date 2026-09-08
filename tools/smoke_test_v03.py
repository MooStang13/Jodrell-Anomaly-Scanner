import numpy as np
from science import distance
x=np.sin(np.linspace(0,2*np.pi,256))**8
y=np.roll(x,37)
z=np.sin(np.linspace(0,2*np.pi,256))**2
d1,*_=distance(x,y); d2,*_=distance(x,z)
print(f'same-shape distance={d1:.4f}')
print(f'different-shape distance={d2:.4f}')
assert d1 < 0.02 and d2 > d1*3
print('v0.3 smoke test PASSED')
