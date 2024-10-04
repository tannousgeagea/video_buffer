import os
import cv2
import matplotlib.pyplot as plt
import numpy as np
import yaml, json
import time
import logging

class Colors:
    # Ultralytics color palette https://ultralytics.com/
    def __init__(self):
        """Initialize colors"""
        self.colors = np.array([
            [0, 255, 0], [0, 0, 255], [255, 128, 0], [255, 153, 51], [255, 178, 102], [230, 230, 0], 
            [255, 153, 255], [153, 204, 255], [255, 102, 255], [255, 51, 255], [102, 178, 255], [51, 153, 255],
            [255, 153, 153], [255, 102, 102], [255, 51, 51], [153, 255, 153], [102, 255, 102],
            [51, 255, 51], [0, 255, 0], [0, 0, 255], [255, 0, 0], [255, 255, 255]
        ],dtype=np.uint8)


class Annotator(Colors):
    def __init__(self, im, line_width=None, font_size=None):
        """Initialize the Annotator class with image and line width """
        self.im = Image(im)
        self.input_shape = self.im.shape
        self.lw = line_width or max(round(sum(im.shape) / 2 * 0.003), 2)  # line width
        self.count = 0
        super(Annotator, self).__init__()

    def box_label(self, box, label='', cls_id=0, color=None, txt_color=None):
        """Add one xyxy box to image with label."""
        
        # set up colors
        color = color if color is not None else tuple(self.colors[cls_id].tolist())

        # cv2
        p1, p2 = (int(box[0]), int(box[1])), (int(box[2]), int(box[3]))
        cv2.rectangle(self.im.data, p1, p2, color, thickness=self.lw, lineType=cv2.LINE_AA)
        if label:
            tf = max(self.lw - 1, 1)  # font thickness
            w, h = cv2.getTextSize(label, 0, fontScale=self.lw / 3, thickness=tf)[0]  # text width, height
            outside = p1[1] - h >= 3
            p2 = p1[0] + w, p1[1] - h - 3 if outside else p1[1] + h + 3
            cv2.rectangle(self.im.data, p1, p2, color, -1, cv2.LINE_AA)  # filled
            cv2.putText(self.im.data,
                        label, (p1[0], p1[1] - 2 if outside else p1[1] + h + 2),
                        0,
                        self.lw / 3,
                        txt_color,
                        thickness=tf,
                        lineType=cv2.LINE_AA)
        

    def draw_mask(self, mask=None, cnt=None, color=None, cls_id=0, alpha=0.5):
        """Plot masks at once.
        Args:
            masks (tensor): predicted masks, shape: [h, w, num_classes]
            color (List[List[Int]]): colors for predicted mask
            alpha (float): mask transparency: 0.0 fully transparent, 1.0 opaque
        """

        # set up colors
        color = color if color is not None else tuple(self.colors[cls_id].tolist())

        if mask is not None:
            mask = np.squeeze(mask)
            if len(mask.shape)==3 and mask.shape[-1]>1:
                # check if the mask is multi-class
                    n_classes = int(mask.shape[-1]) - 1
                    mask = np.argmax(mask, -1).astype('uint8')

            # Create an empty overlay image
            overlay = self.im.data.copy()

            # Overlay the mask on the image using the color map
            for class_index in range(mask.max()):
                overlay[mask == class_index+1] = self.colors[class_index]

            # Apply the overlay on the image
            overlaid = cv2.addWeighted(self.im.data, (1 - alpha), overlay, alpha, 0)
        
        if cnt is not None:
            overlay = self.im.data.copy()
            for c in cnt:
                overlay = cv2.fillPoly(overlay, [c], color)

            self.im.data = cv2.addWeighted(self.im.data, (1 - alpha), overlay, alpha, 0)

    def draw_bbxes(
        self, bbxes, 
        class_ids=[], 
        tracker_id=[], 
        object_size=[],
        outlier_threshold=0.5,
        hoch_threshold=1.0,
        mittel_threshold=1.5,
        label='',
        legend=True,
        show_labels=False,
        show_tracking=False,
        show_object_size=False,
        ):
            
            try:
                for i, bbx in enumerate(bbxes):
                    bbx = (int(bbx[0] * self.input_shape[1]), int(bbx[1] * self.input_shape[0]), int(bbx[2] * self.input_shape[1]), int(bbx[3] * self.input_shape[0]))
                    object_id = tracker_id[i] if len(tracker_id) else 0
                    object_length = object_size[i] if len(object_size) else 0
                    cls_id = class_ids[i] if len(class_ids) else 0
                    
                    _label = label
                    _label = _label + ' ' + f"# {str(object_id)}" if (object_id and show_tracking) else _label
                    _label = self._classes[int(cls_id)] if show_labels else _label
                    _label = _label + ' ' + str(round(object_length * 100)) + ' cm' if show_object_size else _label

                    bbx_color = (0, 255, 0) if object_length < outlier_threshold else (0, 255, 255)
                    bbx_color = bbx_color if object_length < mittel_threshold else (0, 165, 255)
                    bbx_color = bbx_color if object_length < hoch_threshold else (0, 0, 255)

                    self.box_label(bbx, label=_label, cls_id=cls_id, color=bbx_color, txt_color=None)

                if legend:
                    self.legend(self.im.data, 
                                labels=[
                                    f'0 - {int(outlier_threshold * 100)} cm', 
                                    f'{int(outlier_threshold * 100)} - {int(mittel_threshold * 100)} cm',
                                    f'{int(mittel_threshold * 100)} - {int(hoch_threshold * 100)} cm', 
                                    f'> {int(hoch_threshold * 100)} cm'
                                    ],
                                color=(
                                    (0, 255, 0),
                                    (0, 255, 255),
                                    (0, 165, 255),
                                    (0, 0, 255)
                                )
                                )
                    
            except Exception as err:
                logging.error('Error when drawing bbxes: %s' %err)

    def class_label(self, label='', txt_color=None, cls_id=0, color=None):
        color = color if color is not None else tuple(self.colors[cls_id].tolist())
        p1 = (0, 0)
        if label:
            tf = max(self.lw - 1, 1)  # font thickness
            w, h = cv2.getTextSize(label, 0, fontScale=self.lw / 3, thickness=tf)[0]  # text width, height
            p2 = p1[0] + w, p1[1] + h + 3
            cv2.rectangle(self.im.data, p1, p2, color, -1, cv2.LINE_AA)  # filled
            cv2.putText(self.im.data,
                        label, (p1[0], p1[1] + h + 2),
                        0,
                        self.lw / 3,
                        txt_color,
                        thickness=tf,
                        lineType=cv2.LINE_AA)

    def legend(self, 
        img, 
        labels=['0 - 50 cm', '50 - 100 cm', '> 100 cm'], 
        line_width=3, 
        color=((0, 255, 0), (0, 255, 255), (0, 0, 255)), 
        txt_color=None
        ):
        """
        Add a legend to an image to provide context for object size categories.

        This function adds a legend to the input image, displaying labels and corresponding colored rectangles
        that represent different object size categories. The legend enhances visualization by providing information
        about the meaning of different colors used in the image.

        Args:
            img (numpy.ndarray): The input image to which the legend will be added.
            labels (list, optional): Labels for the object size categories. Defaults to ['0 - 50 cm', '50 - 100 cm', '>100cm'].
            line_width (int, optional): Width of the lines used in the legend. Defaults to 1.
            color (tuple or list, optional): List of RGB tuples representing colors for each object size category. Defaults to ((0, 255, 0), (255, 255, 0), (255, 0, 0)).
            txt_color (tuple, optional): Text color for the labels. If None, the color is determined automatically. Defaults to None.

        Returns:
            None: The function modifies the input image by adding the legend.
        """

        tf = max(line_width - 1, 1)
        size = np.array([cv2.getTextSize(l, 0, fontScale=line_width / 4, thickness=tf)[0] for l in labels])
        w, h = np.max(size, axis=0)
        height, width, _ = img.shape
        x_offset = int(w + 10)
        y_offset =  int(h*len(labels) + 40)

        p1 = (int(width - x_offset - 2*int(x_offset / 3)), int(height - y_offset - 5))
        cv2.rectangle(img, (p1[0] - h, p1[1] - 2*h), (width - 5, height - 5), (255, 255, 255), -1, cv2.LINE_AA)
        for i, l in enumerate(labels):
            tf = max(line_width - 1, 1)  # font thickness
            w, h = cv2.getTextSize(l, 0, fontScale=line_width / 4, thickness=tf)[0]
            p2 = p1[0] + w, p1[1] - h + 1
            cv2.rectangle(img, p1, (p1[0] + int(x_offset /3), p1[1] + h - 4), color[i], -1, cv2.LINE_AA)
            cv2.putText(
                img,
                l, (p1[0] + int(x_offset/3) + 5, p1[1] + h + 1),
                0,
                line_width / 3,
                txt_color,
                thickness=tf,
                lineType=cv2.LINE_AA
                )
            p1 = (p1[0], p1[1] + h + 10)


    def add_legend(self, legend_text, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=2, font_thickness=3, legend_color=(255, 255, 255), pos='buttom-left'):

        # Get the size of the legend text
        text_size = cv2.getTextSize(legend_text, font, font_scale, font_thickness)[0]
        position = (5, self.im.data.shape[0] - 5)

        # Calculate the position for the legend at the left bottom of the image
        if pos == "bottom-left":
            position = (5, self.im.data.shape[0] - 5)
        elif pos == "top-left":
            position = (5, 15 + text_size[1])
        

        # Create a rectangle for the legend background
        legend_rect_start = position
        legend_rect_end = (position[0] + text_size[0] + 10, position[1] - text_size[1] - 10)
        cv2.rectangle(self.im.data, legend_rect_start, legend_rect_end, legend_color, cv2.FILLED)

        # Put the legend text on the image
        cv2.putText(self.im.data, legend_text, (position[0] + 5, position[1] - 5),
                    font, font_scale, (0, 0, 0), font_thickness)



class Image:
    """
    A class to represent an image and its different formats.

    Attributes:
        _data: The raw data of the image.
    """
    def __init__(self, data):
        """
        Constructs all the necessary attributes for the image object.

        Parameters:
            data: The raw data of the image.
        """
        self._data = data

    @property
    def data(self):
        """
        Returns the raw image data.

        Returns:
            The raw image data as a NumPy array.
        """
        return self._data

    @data.setter
    def data(self, value):
        """
        Sets the image data.

        Parameters:
            value: The new image data to set.
        """
        self._data = value

    @property
    def shape(self):
        return self.data.shape
    
    @property
    def rgb(self):
        """
        Returns the image in RGB format.

        Returns:
            The image converted to RGB format.
        """
        return self.convert_to_rgb()

    @property
    def bgr(self):
        """
        Returns the image in BGR format.

        Returns:
            The image converted to BGR format.
        """
        return self.convert_to_bgr()

    def convert_to_rgb(self):
        """
        Converts the image to RGB format.

        This is a placeholder method and should be replaced with actual image processing logic.

        Returns:
            The image in RGB format.
        """
        # Placeholder for actual conversion logic
        return cv2.cvtColor(self.data, cv2.COLOR_BGR2RGB)

    def convert_to_bgr(self):
        """
        Converts the image to BGR format.

        This is a placeholder method and should be replaced with actual image processing logic.

        Returns:
            The image in BGR format.
        """
        # Placeholder for actual conversion logic
        return cv2.cvtColor(self.data, cv2.COLOR_RGB2BGR)
    

    