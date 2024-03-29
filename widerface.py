from __future__ import division, print_function

"""WIDER Face Dataset Classes
author: swordli
"""
import os.path as osp
import sys
import torch
import torch.utils.data as data
import cv2
import numpy as np
import scipy.io
import matplotlib.pyplot as plt

plt.switch_backend('agg')

WIDERFace_CLASSES = ['face']  # always index 0
# note: if you used our download scripts, this should be right
WIDERFace_ROOT = "F:\Datasets\人脸识别\WIDERFACE"


class WIDERFaceAnnotationTransform(object):
    def __init__(self, class_to_ind=None):
        self.class_to_ind = class_to_ind or dict(
            zip(WIDERFace_CLASSES, range(len(WIDERFace_CLASSES))))

    def __call__(self, target, width, height):
        for i in range(len(target)):
            target[i][0] = float(target[i][0]) / width
            target[i][1] = float(target[i][1]) / height
            target[i][2] = float(target[i][2]) / width
            target[i][3] = float(target[i][3]) / height
        return target  # [[xmin, ymin, xmax, ymax, label_ind], ... ]


class WIDERFaceDetection(data.Dataset):
    def __init__(self, root,
                 image_sets='train',
                 transform=None, target_transform=WIDERFaceAnnotationTransform(),
                 dataset_name='WIDER Face'):

        self.root = root
        self.image_set = image_sets
        self.transform = transform
        self.target_transform = target_transform
        self.name = dataset_name
        self.img_ids = list()
        self.label_ids = list()
        self.event_ids = list()
        if self.image_set == 'train':
            path_to_label = osp.join(self.root, 'wider_face_split')
            path_to_image = osp.join(self.root, 'WIDER_train/images')
            fname = "wider_face_train.mat"

        if self.image_set == 'val':
            path_to_label = osp.join(self.root, 'wider_face_split')
            path_to_image = osp.join(self.root, 'WIDER_val/images')
            fname = "wider_face_val.mat"

        if self.image_set == 'test':
            path_to_label = osp.join(self.root, 'wider_face_split')
            path_to_image = osp.join(self.root, 'WIDER_test/images')
            fname = "wider_face_test.mat"

        self.path_to_label = path_to_label
        self.path_to_image = path_to_image
        self.fname = fname
        self.f = scipy.io.loadmat(osp.join(self.path_to_label, self.fname))
        self.event_list = self.f.get('event_list')
        self.file_list = self.f.get('file_list')
        self.face_bbx_list = self.f.get('face_bbx_list')

        self._load_widerface()

    def _load_widerface(self):

        error_bbox = 0
        train_bbox = 0
        for event_idx, event in enumerate(self.event_list):
            directory = event[0][0]
            for im_idx, im in enumerate(self.file_list[event_idx][0]):
                im_name = im[0][0]

                if self.image_set in ['test', 'val']:
                    self.img_ids.append(osp.join(self.path_to_image, directory, im_name + '.jpg'))
                    self.event_ids.append(directory)
                    self.label_ids.append([])
                    continue

                face_bbx = self.face_bbx_list[event_idx][0][im_idx][0]
                bboxes = []
                for i in range(face_bbx.shape[0]):
                    # filter bbox
                    if face_bbx[i][2] < 2 or face_bbx[i][3] < 2 or face_bbx[i][0] < 0 or face_bbx[i][1] < 0:
                        error_bbox += 1
                        # print (face_bbx[i])
                        continue
                    train_bbox += 1
                    xmin = float(face_bbx[i][0])
                    ymin = float(face_bbx[i][1])
                    xmax = float(face_bbx[i][2]) + xmin - 1
                    ymax = float(face_bbx[i][3]) + ymin - 1
                    bboxes.append([xmin, ymin, xmax, ymax, 0])

                if (len(bboxes) == 0):  # filter bbox will make bbox none
                    continue
                self.img_ids.append(osp.join(self.path_to_image, directory, im_name + '.jpg'))
                self.event_ids.append(directory)
                self.label_ids.append(bboxes)
                # yield DATA(os.path.join(self.path_to_image, directory,  im_name + '.jpg'), bboxes)

        # self.label_ids = self.label_ids[:32]
        # self.img_ids = self.img_ids[:32]
        # self.event_ids = self.event_ids[:32]
        print("Error bbox number to filter : %d,  bbox number: %d" % (error_bbox, train_bbox))

    def __getitem__(self, index):
        im, gt, h, w = self.pull_item(index)
        return im, gt

    def __len__(self):
        return len(self.img_ids)

    def pull_item(self, index):

        target = self.label_ids[index]
        # print(self.img_ids[index])
        img = cv2.imread(self.img_ids[index])
        # img = cv2.imdecode(np.fromfile(self.img_ids[index], dtype=np.uint8), -1)  # -1表示cv2.IMREAD_UNCHANGED

        height, width, channels = img.shape
        if self.target_transform is not None:
            target = self.target_transform(target, width, height)

        if self.transform is not None:
            target = np.array(target)
            img, boxes, labels = self.transform(img, target[:, :4], target[:, 4])
            target = np.hstack((boxes, np.expand_dims(labels, axis=1)))

        return torch.from_numpy(img).permute(2, 0, 1), target, height, width
        # return img, target, height, width

    def vis_detections(self, im, dets, image_name):

        cv2.imwrite("./tmp_res/" + str(image_name) + "ori.jpg", im)
        print(im)
        size = im.shape[0]
        dets = dets * size
        """Draw detected bounding boxes."""
        class_name = 'face'
        # im = im[:, :, (2, 1, 0)]
        fig, ax = plt.subplots(figsize=(12, 12))
        ax.imshow(im, aspect='equal')

        for i in range(len(dets)):
            bbox = dets[i, :4]
            ax.add_patch(
                plt.Rectangle((bbox[0], bbox[1]),
                              bbox[2] - bbox[0] + 1,
                              bbox[3] - bbox[1] + 1, fill=False,
                              edgecolor='red', linewidth=2.5)
            )
        plt.axis('off')
        plt.tight_layout()
        plt.savefig('./tmp_res/' + str(image_name) + ".jpg", dpi=fig.dpi)

    def vis_detections_v2(self, im, dets, image_name):
        size = im.shape[0]
        dets = dets * size
        """Draw detected bounding boxes."""
        class_name = 'face'
        for i in range(len(dets)):
            bbox = dets[i, :4]
            # print ((bbox[0],bbox[1]), (bbox[2],bbox[3]) )
            cv2.rectangle(im, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), (0, 255, 0), 5)
        cv2.imwrite('./tmp_res/' + str(image_name) + ".jpg", im)

    def pull_image(self, index):
        '''Returns the original image object at index in PIL form

        Note: not using self.__getitem__(), as any transformations passed in
        could mess up this functionality.

        Argument:
            index (int): index of img to show
        Return:
            PIL img
        '''
        return cv2.imdecode(np.fromfile(self.img_ids[index], dtype=np.uint8), -1)  # -1表示cv2.IMREAD_UNCHANGED

    def pull_event(self, index):
        return self.event_ids[index]

    def pull_anno(self, index):
        '''Returns the original annotation of image at index

        Note: not using self.__getitem__(), as any transformations passed in
        could mess up this functionality.

        Argument:
            index (int): index of img to get annotation of
        Return:
            list:  [img_id, [(label, bbox coords),...]]
                eg: ('001718', [('dog', (96, 13, 438, 332))])
        '''
        img_id = self.img_ids[index]
        anno = self.label_ids[index]
        gt = self.target_transform(anno, 1, 1)
        return img_id.split("/")[-1], gt

    def pull_tensor(self, index):
        '''Returns the original image at an index in tensor form

        Note: not using self.__getitem__(), as any transformations passed in
        could mess up this functionality.

        Argument:
            index (int): index of img to show
        Return:
            tensorized version of img, squeezed
        '''
        return torch.Tensor(self.pull_image(index)).unsqueeze_(0)


# from utils.augmentations import SSDAugmentation
if __name__ == '__main__':
    dataset = WIDERFaceDetection(root=WIDERFace_ROOT)
    for i in range(10000):
        img, tar, height, width = dataset.pull_item(i)
        img = img.permute((1, 2, 0)).numpy()
        print(tar)
        cv2.imshow("img", img)
        if cv2.waitKey() == ord('q'):
            break
