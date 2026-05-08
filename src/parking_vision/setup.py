from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'parking_vision'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # launch 파일 등록
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
        # world 파일 등록
        (os.path.join('share', package_name, 'simulation/worlds'),
            glob('simulation/worlds/*.world')),
        # model 파일 등록
        (os.path.join('share', package_name, 'simulation/models/carwash_pillar'),
            glob('simulation/models/carwash_pillar/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zeenee',
    maintainer_email='zeenee@example.com',
    description='Vision-Guided Parking & Carwash Alignment System',
    license='MIT',
    entry_points={
        'console_scripts': [
            'vision_node = parking_vision.vision_node:main',
            'control_node = parking_vision.control_node:main',
        ],
    },
)