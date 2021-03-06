import numpy as np
import numpy as xp

import six
from six import __init__


def _area_of_box(box):
    ymin, xmin, ymax, xmax = box

    return (ymax-ymin) * (xmax-xmin)

def p2bbox(px, py, search_regions, threshold=0.5):
    '''
    use px, py to get bounding boxes from search_regions.
    Args :
        px, py : probability of content. shape of (S, M)
        search_regions : shape of (S, 4), (ymin, xmin, ymax, xmax)

    Return :
        bboxes shape of (S,4)
    '''
    boxes = np.zeros(search_regions.shape)
    # boxes = []

    M = px.shape[1]

    for i in range(px.shape[0]):
        
        x = px[i,:]
        y = py[i,:]

        x = np.where(x>threshold)
        y = np.where(y>threshold)

        # print("x.shape and y.sghape", x[0].shape, y[0].shape)
        # if x[0].any() and y[0].any() :
        if len(x[0])>=5 and len(y[0])>=5 :
            x_s, x_e = x[0][0], x[0][-1]
            y_s, y_e = y[0][0], y[0][-1]
        
            ymin, xmin, ymax, xmax = search_regions[i,:]
            height_block = (ymax - ymin) / M
            width_block = (xmax - xmin) / M

            y_start = ymin + y_s * height_block
            y_end  = ymin + y_e * height_block
            x_start = xmin + x_s * width_block
            x_end  = xmin + x_e * width_block
            
            boxes[i, :] = [y_start, x_start, y_end, x_end]
            # boxes.append([y_start, x_start, y_end, x_end])

    # boxes = np.array(boxes)

    return boxes


def bbox_intersection(box_a, box_b):
    '''
    Args:
        box_a (array): A array of coordinates of a box.
            Its shape is :math:`(4,)`. These coordinates are
            :math:`ymin, xmin, ymax, xmax`.
        box_b (array): A array of coordinates of a box.
            Its shape is :math:`(4,)`. These coordinates are
            :math:`ymin, xmin, ymax, xmax`.
    
    Return:
        intersection (array): A array of coordinates of the intersection box.
            Its shape is :math:`(4,)`. These coordinates are
            :math:`ymin, xmin, ymax, xmax`.
    '''
    y_min_a, x_min_a, y_max_a, x_max_a = box_a
    y_min_b, x_min_b, y_max_b, x_max_b = box_b

    left = max(x_min_a, x_min_b)
    right = min(x_max_a, x_max_b)
    bottom = max(y_min_a, y_min_b)
    top = min(y_max_a, y_max_b)

    # 两个 box 没有交集
    if right<left or top<bottom :
        return np.array([0, 0, 0, 0])
    # 两个 box 有交集，就返回交集的矩形 (ymin, xmin, ymax, xmax)
    else :
        return np.array([bottom, left, top, right])


def bbox2T(search_regions, bboxes, M=28):
    '''
    Encodes the bboxes to Tx and Ty.

    Args:
        search_regions (array): A array of coordinates of search_region.
            Its shape is :math:`(S, 4)`. These coordinates are
            :math:`ymin, xmin, ymax, xmax`.
        bboxes (array): An array of bounding boxes.
            Its shape is :math:`(S, 4)`. These coordinates are
            :math:`ymin, xmin, ymax, xmax`.
        M (int): Number of parts in x or y dorection.

    Returns:
        array:

    '''

    intersections = np.zeros(search_regions.shape)

    for ii, (search_region, bbox) in enumerate(zip(search_regions, bboxes)):
        intersection = bbox_intersection(search_region, bbox)

        if _area_of_box(intersection):
            intersections[ii,:] = intersection
    

    Tx = np.zeros((search_regions.shape[0], M))
    Ty = np.zeros((search_regions.shape[0], M))


    for jj, (search_region, intersection) in enumerate(zip(search_regions, intersections)):
        
        if _area_of_box(intersection):

            ymin, xmin, ymax, xmax = search_region
            bottom, left, top, right = intersection

            # xmin~xmax段M等分，设等分尺寸为dx
            # x在(left-dx, right+dx)的开区间内，对应的label就是1，否则是0   
            dx = (xmax-xmin)/(M-1)
            tx = []
            for x in np.linspace(xmin, xmax, num=M):
                if left-dx < x < right+dx:
                    tx.append(1)
                else:
                    tx.append(0)

            Tx[jj,:] = np.array(tx)
            
            # ymin~ymax段M等分，设等分尺寸为dy
            # y在(bottom-dy, top+dy)的开区间内，对应的label就是1，否则是0 
            dy = (ymax-ymin)/(M-1)
            ty = []
            for y in np.linspace(ymin, ymax, num=M):
                if bottom-dy < y < top+dy:
                    ty.append(1)
                else:
                    ty.append(0)

            Ty[jj,:] = np.array(ty)
    
    # Tx can be all 0, because some of search_regions are negtive. 
    # if (np.max(Tx))== 0:
    #     print("Tx all zeros!!!!")
 
    return Tx, Ty


def loc2bbox(src_bbox, loc):
    """Decode bounding boxes from bounding box offsets and scales.

    Given bounding box offsets and scales computed by
    :meth:`bbox2loc`, this function decodes the representation to
    coordinates in 2D image coordinates.

    Given scales and offsets :math:`t_y, t_x, t_h, t_w` and a bounding
    box whose center is :math:`(y, x) = p_y, p_x` and size :math:`p_h, p_w`,
    the decoded bounding box's center :math:`\\hat{g}_y`, :math:`\\hat{g}_x`
    and size :math:`\\hat{g}_h`, :math:`\\hat{g}_w` are calculated
    by the following formulas.

    * :math:`\\hat{g}_y = p_h t_y + p_y`
    * :math:`\\hat{g}_x = p_w t_x + p_x`
    * :math:`\\hat{g}_h = p_h \\exp(t_h)`
    * :math:`\\hat{g}_w = p_w \\exp(t_w)`

    The decoding formulas are used in works such as R-CNN [#]_.

    The output is same type as the type of the inputs.

    .. [#] Ross Girshick, Jeff Donahue, Trevor Darrell, Jitendra Malik. \
    Rich feature hierarchies for accurate object detection and semantic \
    segmentation. CVPR 2014.

    Args:
        src_bbox (array): A coordinates of bounding boxes.
            Its shape is :math:`(R, 4)`. These coordinates are
            :math:`p_{ymin}, p_{xmin}, p_{ymax}, p_{xmax}`.
        loc (array): An array with offsets and scales.
            The shapes of :obj:`src_bbox` and :obj:`loc` should be same.
            This contains values :math:`t_y, t_x, t_h, t_w`.

    Returns:
        array:
        Decoded bounding box coordinates. Its shape is :math:`(R, 4)`. \
        The second axis contains four values \
        :math:`\\hat{g}_{ymin}, \\hat{g}_{xmin},
        \\hat{g}_{ymax}, \\hat{g}_{xmax}`.

    """

    if src_bbox.shape[0] == 0:
        return xp.zeros((0, 4), dtype=loc.dtype)

    src_bbox = src_bbox.astype(src_bbox.dtype, copy=False)

    src_height = src_bbox[:, 2] - src_bbox[:, 0]
    src_width = src_bbox[:, 3] - src_bbox[:, 1]
    src_ctr_y = src_bbox[:, 0] + 0.5 * src_height
    src_ctr_x = src_bbox[:, 1] + 0.5 * src_width

    dy = loc[:, 0::4]
    dx = loc[:, 1::4]
    dh = loc[:, 2::4]
    dw = loc[:, 3::4]

    # print("dh = ", dh)

    ctr_y = dy * src_height[:, xp.newaxis] + src_ctr_y[:, xp.newaxis]
    ctr_x = dx * src_width[:, xp.newaxis] + src_ctr_x[:, xp.newaxis]
    h = xp.exp(dh) * src_height[:, xp.newaxis]
    w = xp.exp(dw) * src_width[:, xp.newaxis]

    dst_bbox = xp.zeros(loc.shape, dtype=loc.dtype)
    dst_bbox[:, 0::4] = ctr_y - 0.5 * h
    dst_bbox[:, 1::4] = ctr_x - 0.5 * w
    dst_bbox[:, 2::4] = ctr_y + 0.5 * h
    dst_bbox[:, 3::4] = ctr_x + 0.5 * w

    return dst_bbox


def bbox2loc(src_bbox, dst_bbox):
    """Encodes the source and the destination bounding boxes to "loc".

    Given bounding boxes, this function computes offsets and scales
    to match the source bounding boxes to the target bounding boxes.
    Mathematcially, given a bounding box whose center is
    :math:`(y, x) = p_y, p_x` and
    size :math:`p_h, p_w` and the target bounding box whose center is
    :math:`g_y, g_x` and size :math:`g_h, g_w`, the offsets and scales
    :math:`t_y, t_x, t_h, t_w` can be computed by the following formulas.

    * :math:`t_y = \\frac{(g_y - p_y)} {p_h}`
    * :math:`t_x = \\frac{(g_x - p_x)} {p_w}`
    * :math:`t_h = \\log(\\frac{g_h} {p_h})`
    * :math:`t_w = \\log(\\frac{g_w} {p_w})`

    The output is same type as the type of the inputs.
    The encoding formulas are used in works such as R-CNN [#]_.

    .. [#] Ross Girshick, Jeff Donahue, Trevor Darrell, Jitendra Malik. \
    Rich feature hierarchies for accurate object detection and semantic \
    segmentation. CVPR 2014.

    Args:
        src_bbox (array): An image coordinate array whose shape is
            :math:`(R, 4)`. :math:`R` is the number of bounding boxes.
            These coordinates are
            :math:`p_{ymin}, p_{xmin}, p_{ymax}, p_{xmax}`.
        dst_bbox (array): An image coordinate array whose shape is
            :math:`(R, 4)`.
            These coordinates are
            :math:`g_{ymin}, g_{xmin}, g_{ymax}, g_{xmax}`.

    Returns:
        array:
        Bounding box offsets and scales from :obj:`src_bbox` \
        to :obj:`dst_bbox`. \
        This has shape :math:`(R, 4)`.
        The second axis contains four values :math:`t_y, t_x, t_h, t_w`.

    """

    height = src_bbox[:, 2] - src_bbox[:, 0]
    width = src_bbox[:, 3] - src_bbox[:, 1]
    ctr_y = src_bbox[:, 0] + 0.5 * height
    ctr_x = src_bbox[:, 1] + 0.5 * width

    base_height = dst_bbox[:, 2] - dst_bbox[:, 0]
    base_width = dst_bbox[:, 3] - dst_bbox[:, 1]
    base_ctr_y = dst_bbox[:, 0] + 0.5 * base_height
    base_ctr_x = dst_bbox[:, 1] + 0.5 * base_width

    eps = xp.finfo(height.dtype).eps
    height = xp.maximum(height, eps)
    width = xp.maximum(width, eps)

    dy = (base_ctr_y - ctr_y) / height
    dx = (base_ctr_x - ctr_x) / width
    dh = xp.log(base_height / height)
    dw = xp.log(base_width / width)

    loc = xp.vstack((dy, dx, dh, dw)).transpose()
    return loc


def bbox_iou(bbox_a, bbox_b):
    """Calculate the Intersection of Unions (IoUs) between bounding boxes.

    IoU is calculated as a ratio of area of the intersection
    and area of the union.

    This function accepts both :obj:`numpy.ndarray` and :obj:`cupy.ndarray` as
    inputs. Please note that both :obj:`bbox_a` and :obj:`bbox_b` need to be
    same type.
    The output is same type as the type of the inputs.

    Args:
        bbox_a (array): An array whose shape is :math:`(N, 4)`.
            :math:`N` is the number of bounding boxes.
            The dtype should be :obj:`numpy.float32`.
        bbox_b (array): An array similar to :obj:`bbox_a`,
            whose shape is :math:`(K, 4)`.
            The dtype should be :obj:`numpy.float32`.

    Returns:
        array:
        An array whose shape is :math:`(N, K)`. \
        An element at index :math:`(n, k)` contains IoUs between \
        :math:`n` th bounding box in :obj:`bbox_a` and :math:`k` th bounding \
        box in :obj:`bbox_b`.

    """
    if bbox_a.shape[1] != 4 or bbox_b.shape[1] != 4:
        raise IndexError

    # top left
    tl = xp.maximum(bbox_a[:, None, :2], bbox_b[:, :2])
    # bottom right
    br = xp.minimum(bbox_a[:, None, 2:], bbox_b[:, 2:])

    area_i = xp.prod(br - tl, axis=2) * (tl < br).all(axis=2)
    area_a = xp.prod(bbox_a[:, 2:] - bbox_a[:, :2], axis=1)
    area_b = xp.prod(bbox_b[:, 2:] - bbox_b[:, :2], axis=1)
    return area_i / (area_a[:, None] + area_b - area_i)


def __test():
    pass


if __name__ == '__main__':
    __test()


def generate_anchor_base(base_size=16, ratios=[0.5, 1, 2],
                         anchor_scales=[8, 16, 32]):
    """Generate anchor base windows by enumerating aspect ratio and scales.

    Generate anchors that are scaled and modified to the given aspect ratios.
    Area of a scaled anchor is preserved when modifying to the given aspect
    ratio.

    :obj:`R = len(ratios) * len(anchor_scales)` anchors are generated by this
    function.
    The :obj:`i * len(anchor_scales) + j` th anchor corresponds to an anchor
    generated by :obj:`ratios[i]` and :obj:`anchor_scales[j]`.

    For example, if the scale is :math:`8` and the ratio is :math:`0.25`,
    the width and the height of the base window will be stretched by :math:`8`.
    For modifying the anchor to the given aspect ratio,
    the height is halved and the width is doubled.

    Args:
        base_size (number): The width and the height of the reference window.
        ratios (list of floats): This is ratios of width to height of
            the anchors.
        anchor_scales (list of numbers): This is areas of anchors.
            Those areas will be the product of the square of an element in
            :obj:`anchor_scales` and the original area of the reference
            window.

    Returns:
        ~numpy.ndarray:
        An array of shape :math:`(R, 4)`.
        Each element is a set of coordinates of a bounding box.
        The second axis corresponds to
        :math:`(y_{min}, x_{min}, y_{max}, x_{max})` of a bounding box.

    """
    py = base_size / 2.
    px = base_size / 2.

    anchor_base = np.zeros((len(ratios) * len(anchor_scales), 4),
                           dtype=np.float32)
    for i in six.moves.range(len(ratios)):
        for j in six.moves.range(len(anchor_scales)):
            h = base_size * anchor_scales[j] * np.sqrt(ratios[i])
            w = base_size * anchor_scales[j] * np.sqrt(1. / ratios[i])

            index = i * len(anchor_scales) + j
            anchor_base[index, 0] = py - h / 2.
            anchor_base[index, 1] = px - w / 2.
            anchor_base[index, 2] = py + h / 2.
            anchor_base[index, 3] = px + w / 2.
    return anchor_base
