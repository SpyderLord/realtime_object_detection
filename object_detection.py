#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Dec 21 12:01:40 2017

@author: GustavZ
"""
import numpy as np
import os
import six.moves.urllib as urllib
import tarfile
import tensorflow as tf
import cv2

# Protobuf Compilation (once necessary)
#os.system('protoc object_detection/protos/*.proto --python_out=.')

from object_detection.utils import label_map_util
from object_detection.utils import visualization_utils as vis_util
from stuff.helper import FPS2, WebcamVideoStream


def download_model(model_name=None, model_path=None):
    if model_name is None:
        model_name = 'ssd_mobilenet_v11_coco'
    if model_path is None:
        model_path = 'models/' + model_name + '/frozen_inference_graph.pb'
    
    model_file = model_name + '.tar.gz'
    download_base = 'http://download.tensorflow.org/models/object_detection/'   
    if not os.path.isfile(model_path):
        print('Model not found. Downloading it now.')
        opener = urllib.request.URLopener()
        opener.retrieve(download_base + model_file, model_file)
        tar_file = tarfile.open(model_file)
        for file in tar_file.getmembers():
          file_name = os.path.basename(file.name)
          if 'frozen_inference_graph.pb' in file_name:
            tar_file.extract(file, os.getcwd() + '/models/')
        os.remove(os.getcwd() + '/' + model_file)
    else:
        print('Model found. Proceed.')
        
        
def load_frozenmodel(model_name=None, model_path=None, label_path=None, num_classes=90):
    if model_name is None:
        model_name = 'ssd_mobilenet_v11_coco'
    if model_path is None:
        model_path = 'models/' + model_name + '/frozen_inference_graph.pb'
    if label_path is None:
        label_path = 'object_detection/data/mscoco_label_map.pbtxt'
    # Load a (frozen) Tensorflow model into memory.
    detection_graph = tf.Graph()
    with detection_graph.as_default():
      od_graph_def = tf.GraphDef()
      with tf.gfile.GFile(model_path, 'rb') as fid:
        serialized_graph = fid.read()
        od_graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(od_graph_def, name='')
    # Loading label map
    label_map = label_map_util.load_labelmap(label_path)
    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=num_classes, use_display_name=True)
    category_index = label_map_util.create_category_index(categories)
    return detection_graph, category_index
    

def detection(detection_graph, category_index, video_input=0, visualize=True, max_frames=500, 
              width=300 , height=300, fps_interval=3, allow_memory_growth=True , det_intervall=75, det_th=0.5):
    
    # Session Config: Limit GPU Memory Usage
    config = tf.ConfigProto()
    config.gpu_options.allow_growth=allow_memory_growth
    
    cur_frames = 0
    # Detection
    with detection_graph.as_default():
      with tf.Session(graph=detection_graph, config = config) as sess:
        # Definite input and output Tensors for detection_graph
        image_tensor = detection_graph.get_tensor_by_name('image_tensor:0')
        # Each box represents a part of the image where a particular object was detected.
        detection_boxes = detection_graph.get_tensor_by_name('detection_boxes:0')
        # Each score represent how level of confidence for each of the objects.
        # Score is shown on the result image, together with the class label.
        detection_scores = detection_graph.get_tensor_by_name('detection_scores:0')
        detection_classes = detection_graph.get_tensor_by_name('detection_classes:0')
        num_detections = detection_graph.get_tensor_by_name('num_detections:0')
        # fps calculation
        fps = FPS2(fps_interval).start()
        # Start Video Stream
        video_stream = WebcamVideoStream(video_input,width,height).start()
        print ("Press 'q' to Exit")
        while video_stream.isActive():
          image_np = video_stream.read()
          # Expand dimensions since the model expects images to have shape: [1, None, None, 3]
          image_np_expanded = np.expand_dims(image_np, axis=0)
          # Actual detection.
          (boxes, scores, classes, num) = sess.run(
              [detection_boxes, detection_scores, detection_classes, num_detections],
              feed_dict={image_tensor: image_np_expanded})
          if visualize:
              # Visualization of the results of a detection.
              vis_util.visualize_boxes_and_labels_on_image_array(
              image_np,
              np.squeeze(boxes),
              np.squeeze(classes).astype(np.int32),
              np.squeeze(scores),
              category_index,
              use_normalized_coordinates=True,
              line_thickness=8)
              cv2.imshow('object_detection', image_np)
              # Exit Option
              if cv2.waitKey(1) & 0xFF == ord('q'):
                  break
          else:
              cur_frames += 1
              for box, score, _class in zip(np.squeeze(boxes), np.squeeze(scores), np.squeeze(classes)):
                    if cur_frames%det_intervall==0 and score > det_th:
                        label = category_index[_class]['name']
                        print(label, score, box)
              if cur_frames >= max_frames:
                  break
          # fps calculation
          fps.update()
    
    # End everything
    fps.stop()
    video_stream.stop()     
    cv2.destroyAllWindows()
    print('[INFO] elapsed time (total): {:.2f}'.format(fps.elapsed()))
    print('[INFO] approx. FPS: {:.2f}'.format(fps.fps()))

def main():
    '''
    ############## INPUT PARAMS ##############
    # those values are default for detection #
    # if you want to change them, uncomment  #
    # and pass them to the detection() fun   #
    #                                        #
    video_input = 0              # Input Must be OpenCV readable 
    visualize = True             # Disable for performance increase
    max_frames = 500             # only used if visualize==False
    width = 300                  # 300x300 is used by SSD_Mobilenet -> highest fps
    height = 300
    fps_interval = 3             # Intervall [s] to print fps in console
    allow_memory_growth = True   # restart python to apply changes on memory usage
    det_intervall = 75           # intervall [frames] to print detections to console
    det_th = 0.5                 # detection threshold for det_intervall
    #                                        #
    ##########################################
    '''
                                    # Optional Arguments
    download_model()                # model_name, model_path
    dg, ci = load_frozenmodel()     # model_name, model_path, label_path, num_classes
    detection(dg, ci)               # video_input, visualize, max_frames, width , height, fps_interval, allow_memory_growth , det_intervall, det_th
    
    
if __name__ == '__main__':
    main()
