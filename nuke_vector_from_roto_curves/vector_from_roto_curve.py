import nuke
import math

def calculate_vector(p1, p2):
    """
    function to calculate vector between two given points
    """
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    length = math.sqrt(dx**2 + dy**2)
    if length == 0:
        return (0.0, 0.0)
    return (dx / length, dy / length)

# arbitrary number to choose the "resolution", number of points we want to evaluate along the curve
num_samples = 100

# Get the selected node (should be a rotopaint one)
roto_node = nuke.selectedNode()

if roto_node.Class() not in ['Roto', 'RotoPaint']:
    nuke.message("Sselect Rotopaint node pleeeease.")
else:
    root_layer = roto_node['curves']
    shape_list = root_layer.rootLayer

    for shape in shape_list:
        if isinstance(shape, nuke.rotopaint.Shape):
            main_curve = shape.evaluate(0, 1)  # Frame 1, if we want animated strokes we should update this part

            sampled_positions = []
            vectors = []

            # uniform sampling between 0 and 1
            for i in range(num_samples):
                t = float(i) / float(num_samples - 1)
                point = main_curve.getPoint(t)
                sampled_positions.append(point)

            # vector calculation over the sampled points on curve
            for i in range(len(sampled_positions) - 1):
                p1 = sampled_positions[i]
                p2 = sampled_positions[i + 1]
                vec = calculate_vector(p1, p2)
                vectors.append(vec)

            print("Sampled Points:")
            for i, p in enumerate(sampled_positions):
                print(f"{i}: ({p.x:.2f}, {p.y:.2f})")

            print("\nDirection Vectors:")
            for i, v in enumerate(vectors):
                print(f"{i}: dx={v[0]:.3f}, dy={v[1]:.3f}")