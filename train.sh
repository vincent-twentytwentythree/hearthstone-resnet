python train.py --gpu_devices 0,1,2,3,4,5,6,7 --num_actor_devices 6 --num_actors 6 --training_device 7 --save_interval 20 --load_model
#python train.py --gpu_devices 0,1,2,3,4,5,6,7 --num_actor_devices -3 --num_actors 6 --training_device 4 --save_interval 20 --load_model
#python train.py --gpu_devices 0 --num_actor_devices 1 --num_actors 1 --training_device 0 --load_model --save_interval 20 --learning_rate 0.001 --alpha 0.9 --momentum 0.9
#python train.py --gpu_devices 5,6 --num_actor_devices 1 --num_actors 1 --training_device 6 --load_model --save_interval 20 --learning_rate 0.001 --alpha 0.9 --momentum 0.9
