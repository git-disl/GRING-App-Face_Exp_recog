import torch
import torchvision.transforms as transforms
import numpy as np
import csv
from PIL import Image
from torchvision.transforms import ToTensor
from torch.utils.data import DataLoader

batch_size = 128
shape = (44, 44)

class DataSetFactory:

    def __init__(self):
        images = []
        emotions = []
        private_images = []
        private_emotions = []
        public_images = []
        public_emotions = []

        print('Reading dataset..')
        with open('./dataset/fer2013.csv', 'r') as csvin:
            data = csv.reader(csvin)
            next(data)
            for row in data:
                face = [int(pixel) for pixel in row[1].split()]
                face = np.asarray(face).reshape(48, 48)
                face = face.astype('uint8')

                if row[-1] == 'Training':
                    emotions.append(int(row[0]))
                    images.append(Image.fromarray(face))
                elif row[-1] == "PrivateTest":
                    private_emotions.append(int(row[0]))
                    private_images.append(Image.fromarray(face))
                elif row[-1] == "PublicTest":
                    public_emotions.append(int(row[0]))
                    public_images.append(Image.fromarray(face))

        self.num_train = len(images)
        self.num_valid = len(private_images)
        self.num_test = len(public_images)

        print('training size %d :validate size %d : test size %d' % (
            self.num_train, self.num_valid, self.num_test))

        train_transform = transforms.Compose([
            transforms.RandomCrop(shape[0]),
            transforms.RandomHorizontalFlip(),
            ToTensor(),
        ])
        val_transform = transforms.Compose([
            transforms.CenterCrop(shape[0]),
            ToTensor(),
        ])

        training = DataSet(transform=train_transform, images=images, emotions=emotions)
        private = DataSet(transform=val_transform, images=private_images, emotions=private_emotions)
        public = DataSet(transform=val_transform, images=public_images, emotions=public_emotions)

        self.classes = ['Angry', 'Disgust', 'Fear', 'Happy', 'Sad', 'Surprise', 'Neutral']

        self.train_loader = DataLoader(training, batch_size=batch_size, shuffle=True, num_workers=1)
        self.valid_loader = DataLoader(private, batch_size=batch_size, shuffle=True, num_workers=1)
        self.test_loader = DataLoader(public, batch_size=batch_size, shuffle=True, num_workers=1)


class DataSet(torch.utils.data.Dataset):

    def __init__(self, transform=None, images=None, emotions=None):
        self.transform = transform
        self.images = images
        self.emotions = emotions

    def __getitem__(self, index):
        image = self.images[index]
        emotion = self.emotions[index]
        if self.transform is not None:
            image = self.transform(image)
        return image, emotion

    def __len__(self):
        return len(self.images)

if __name__ == "__main__":
    m = DataSetFactory()

