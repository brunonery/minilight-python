#  MiniLight Python : minimal global illumination renderer
#
#  Copyright (c) 2007-2008, Harrison Ainsworth / HXA7241 and Juraj Sukop.
#  http://www.hxa7241.org/


from math import log10
from vector3f import Vector3f

PPM_ID = 'P6'
MINILIGHT_URI = 'http://www.hxa7241.org/minilight/'
DISPLAY_LUMINANCE_MAX = 200.0
RGB_LUMINANCE = Vector3f(0.2126, 0.7152, 0.0722)
GAMMA_ENCODE = 0.45

class Image(object):

    def __init__(self, in_stream):
        for line in in_stream:
            if not line.isspace():
                self.width, self.height = map(lambda dimension: min(max(1, int(dimension)), 10000), line.split())
                self.pixels = [0.0] * self.width * self.height * 3
                break

    def add_to_pixel(self, x, y, radiance):
        if x >= 0 and x < self.width and y >= 0 and y < self.height:
            index = (x + ((self.height - 1 - y) * self.width)) * 3
            for a in radiance:
                self.pixels[index] += a
                index += 1

    def get_formatted(self, out, iteration):
        divider = 1.0 / ((iteration if iteration > 0 else 0) + 1)
        tonemap_scaling = self.calculate_tone_mapping(self.pixels, divider)
        out.write('%s\n# %s\n\n%u %u\n255\n' % (PPM_ID, MINILIGHT_URI, self.width, self.height))
        for channel in self.pixels:
            mapped = channel * divider * tonemap_scaling
            gammaed = (mapped if mapped > 0.0 else 0.0) ** GAMMA_ENCODE
            out.write(chr(min(int((gammaed * 255.0) + 0.5), 255)))

    def get_distance_image(self, out, iteration):
        divider = 1.0 / ((iteration if iteration > 0 else 0) + 1)
        max_scaling = 1.0 / max(self.pixels)
        out.write('%s\n# %s\n\n%u %u\n65535\n' % (PPM_ID, MINILIGHT_URI, self.width, self.height))
        for channel in self.pixels:
            # 16-bit PPM :)
            mapped = int(min(channel * max_scaling * 65535.0, 65535))
            first_byte = (mapped & 0xFF00) >> 8
            second_byte = (mapped & 0x00FF)
            out.write(chr(first_byte))
            out.write(chr(second_byte))

    def get_ply_map(self, out, iteration):
        divider = 1.0 / ((iteration if iteration > 0 else 0) + 1)
        cu = self.width / 2
        cv = self.height / 2
        # The fu and fv formulae were obtained empirically by analysing the
        # output of minilight_depth.py for cube.txt with 72x72, 200x200 and
        # 400x400 resolutions. It's not exact as the rendering depends on a
        # random factor.
        fu = 5.73 * self.width
        fv = 5.73 * self.height
        n_points = len([p for p in self.pixels if p > 0])/3
        out.write('ply\n')
        out.write('format ascii 1.0\n')
        out.write('element vertex %d\n' % n_points)
        out.write('property float x\n')
        out.write('property float y\n')
        out.write('property float z\n')
        out.write('end_header\n')
        for u in range(self.width):
            for v in range(self.height):
                index = (u + ((self.height - 1 - v) * self.width)) * 3
                z = self.pixels[index] * divider
                x = (u - cu) * z / fu
                y = (v - cv) * z / fv
                # No distance means we didn't render anything in this pixel.
                if z > 0:
                    out.write('%f %f %f\n' % (x, y, z))

    def calculate_tone_mapping(self, pixels, divider):
        sum_of_logs = 0.0
        for i in range(len(pixels) / 3):
            y = Vector3f(pixels[i * 3: i * 3 + 3]).dot(RGB_LUMINANCE) * divider
            sum_of_logs += log10(y if y > 1e-4 else 1e-4)
        log_mean_luminance = 10.0 ** (sum_of_logs / (len(pixels) / 3))
        a = 1.219 + (DISPLAY_LUMINANCE_MAX * 0.25) ** 0.4
        b = 1.219 + log_mean_luminance ** 0.4
        return ((a / b) ** 2.5) / DISPLAY_LUMINANCE_MAX
