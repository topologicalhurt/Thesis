import sys
import os
import math
import numpy as np
import itertools
from scipy.spatial import ConvexHull, Delaunay

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'Src'))

from helpers import sign


# TODO:
# (1) 'Inflate' the surface vertices such that the old polytope is completely circumscribed
# (2) Use R*-tree or Hilbert R-tree to find volume contributions of the top n densest packed regions
# (I.e. same as using the metric on points, but for packings of points)
# (3) Use some kind of statistical measure to get a probability of an initial buy-in


class Tri():

    def __init__(self, simplice):
        self.simplice = simplice

    @staticmethod
    def findfacet(p, simplice):
        # https://stackoverflow.com/a/16000405/10019450
        print(p, simplice)
        c,b,a = simplice
        b1 = sign(p,a,b) < 0.0
        b2 = sign(p,b,c) < 0.0
        b3 = sign(p,c,a) < 0.0
        return b1 == b2 == b3

    def __contains__(self, point):
        return Tri.findfacet(point, self.simplice)


class FindHMetric():
    def __init__(self, points):
        self.points = points
        self.hull = ConvexHull(self.points)
        self.delaunay = Delaunay(self.points)

        self.volumes = []
        for simplex in self.delaunay.simplices:
            simplex_points = self.points[simplex]
            vectors = simplex_points[1:] - simplex_points[0]
            vol = abs(np.linalg.det(vectors)) / math.factorial(self.points.shape[0])
            self.volumes.append(vol)

        [self.point_contributions, self.total_volume] = self.distribute_hull_volume()

    def distribute_hull_volume(self):
        """
        Calculate volume contribution for each point where the sum
        equals the total convex hull volume.
        """
        total_hull_volume = self.hull.volume
        n_points = len(self.points)
        point_contributions = np.zeros(n_points)

        # Count participation of each point
        point_participation = np.zeros(n_points)
        for simplex in self.delaunay.simplices:
            for idx in simplex:
                point_participation[idx] += 1

        for i, simplex in enumerate(self.delaunay.simplices):
            tetra_volume = self.volumes[i]

            # Distribute volume inversely proportional to point participation count
            # Points that participate in fewer tetrahedra are more critical
            for idx in simplex:
                weight = 1.0 / point_participation[idx]
                point_contributions[idx] += weight * tetra_volume

        # Normalize to the total hull volume
        point_contributions = point_contributions / np.sum(point_contributions) * total_hull_volume

        return point_contributions, total_hull_volume

    def find_top_volume_contributors(self, n='all'):
        """
        Find the n points that contribute most to the convex hull volume.

        Args:
            points: numpy array of shape (num_points, dimension)
            n: number of top contributing points to return
            surface_only: determines if only points on surface of convex hull considered

        Returns:
            indices of the n most important points, sorted by contribution
        """

        n_points = len(self.points)
        n = n_points if n == 'all' else n
        volumes_without_point = np.full(n_points, self.hull.volume)

        # Calculate volume, 'pruning' each considered point
        for i, p in enumerate(self.points):
            for simplice in self.delaunay.simplices[i]:
                tri = Tri(self.points[simplice])
                if p in tri:
                    volumes_without_point -= self.volumes[i]

        # Calculate volume contribution of each point
        volume_contributions = self.hull.volume - volumes_without_point
        n = min(n, n_points)
        return [(idx, volume_contributions[idx], (volume_contributions[idx] / self.hull.volume))
                for idx in np.argsort(volume_contributions)[-n:][::-1]]

    def visualize_volume_distribution(self, save_path=None):
        """
        Visualize the volume distribution within a convex hull.
        """
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection

        if self.points.shape[1] != 3:
            raise ValueError('This visualization only works with 3D points')

        # Set up the figure
        fig = plt.figure(figsize=(12, 10))
        ax = fig.add_subplot(111, projection='3d')

        # Plot the convex hull wireframe
        for simplex in self.hull.simplices:
            hull_points = self.points[simplex]
            ax.plot3D(
                hull_points[[0, 1, 2, 0], 0],
                hull_points[[0, 1, 2, 0], 1],
                hull_points[[0, 1, 2, 0], 2],
                'red', linewidth=2
            )

        # Generate unique colors for each tetrahedron
        cmap = plt.cm.get_cmap('viridis', len(self.delaunay.simplices))

        # Plot each tetrahedron with a different color
        for i, simplex in enumerate(self.delaunay.simplices):
            tetra_points = self.points[simplex]

            # I.e. Arrange as tetrahedron C0: 0 0 0 1, C1: 1 1 2 2, C2: 2 3 3 3
            face_indices = np.array(
                list(itertools.combinations(
                    range(len(tetra_points)), 3)
                )
            )
            faces = [[tetra_points[i] for i in ro] for ro in face_indices]

            # Add each tetrahedron as a transparent colored surface
            tetra = Poly3DCollection(faces, alpha=0.2)
            tetra.set_color(cmap(i))
            ax.add_collection3d(tetra)

            # Display volume percentage for larger tetrahedra
            if self.volumes[i] / self.total_volume > 0.05:
                centroid = np.mean(tetra_points, axis=0)
                ax.text(centroid[0], centroid[1], centroid[2],
                    f'{self.volumes[i] / self.total_volume*100:.1f}%', size=8)

        # Plot the points with size proportional to their volume contribution
        max_contrib = np.max(self.point_contributions)
        sizes = 1000 * (self.point_contributions / max_contrib)
        scatter = ax.scatter(
            self.points[:, 0], self.points[:, 1], self.points[:, 2],
            c=self.point_contributions, s=sizes, cmap='plasma',
            alpha=0.7, edgecolors='black'
        )

        # Calculate and display sum verification
        contribution_sum = np.sum(self.point_contributions)
        stats = (
            f'Total Hull Volume: {self.total_volume:.4f}\n'
            f'Sum of Point Contributions: {contribution_sum:.4f}\n'
            f'Verification Ratio: {contribution_sum / self.total_volume:.6f}\n'
            f'Points: {len(self.points)}, Tetrahedra: {len(self.delaunay.simplices)}'
        )
        ax.text2D(0.05, 0.95, stats, transform=ax.transAxes,
                fontsize=10, bbox=dict(facecolor='white', alpha=0.7))

        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title('Volume Distribution in Convex Hull (Normalized)')
        ax.view_init(elev=30, azim=45)

        cbar = fig.colorbar(scatter, ax=ax, shrink=0.6)
        cbar.set_label('Volume Contribution')

        if save_path is not None:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')

        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    np.random.seed(0)
    n_pts = 10
    n_accepted = n_pts // 2
    points = np.random.rand(n_pts, 3)

    H_metric = FindHMetric(points)

    top_vols = H_metric.find_top_volume_contributors(n_accepted)
    top_vols_total_percent = 100 * sum(pt[2] for pt in top_vols)
    print(
        f'\tExpected \033[4mglobal\033[0m avg: {100 / n_pts:.3f}'
        f'\n\tExpected \033[4maccepted\033[0m avg: {top_vols_total_percent / n_accepted:.3f}'
        f'\n\tThis is an ~ {(top_vols_total_percent * n_pts) / (100 * n_accepted):.2f}x increase '
        f'accounting for {top_vols_total_percent:.3f}% total volume'
    )

    H_metric.visualize_volume_distribution()
