from tqdm import tqdm
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import io
import sys

import model
import datasource

import medmnist
from medmnist import Evaluator

NUM_EPOCHS = 1
lr = 0.001

datasource = datasource.MedMNIST()

# define loss function and optimizer
if datasource.task == "multi-label, binary-class":
    criterion = nn.BCEWithLogitsLoss()
else:
    criterion = nn.CrossEntropyLoss()

mymodel = model.Net(in_channels=datasource.n_channels, num_classes=datasource.n_classes)

optimizer = optim.SGD(mymodel.parameters(), lr=lr, momentum=0.9)

def train():
    train_losses=[]
    train_accu=[]
    for epoch in range(NUM_EPOCHS):
        train_correct = 0
        train_total = 0
        test_correct = 0
        test_total = 0

        running_loss = 0
        correct = 0
        total = 0
		        
        mymodel.train()
        for inputs, targets in tqdm(datasource.train_loader):
            # forward + backward + optimize
            optimizer.zero_grad()
            outputs = mymodel(inputs)
						            
            if datasource.task == 'multi-label, binary-class':
                targets = targets.to(torch.float32)
                loss = criterion(outputs, targets)
            else:
                targets = targets.squeeze().long()
                loss = criterion(outputs, targets)
					            
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

        train_loss=running_loss/len(datasource.train_loader)
        accu=100.*correct/total

        train_accu.append(accu)
        train_losses.append(train_loss)
        print('Train Loss: %.3f | Accuracy: %.3f'%(train_loss,accu))

def test(split):
    mymodel.eval()
    y_true = torch.tensor([])
    y_score = torch.tensor([])
	        
    data_loader = datasource.train_loader_at_eval if split == 'train' else datasource.test_loader

    with torch.no_grad():
        for inputs, targets in data_loader:
            outputs = mymodel(inputs)

            if datasource.task == 'multi-label, binary-class':
                targets = targets.to(torch.float32)
                outputs = outputs.softmax(dim=-1)
            else:
                targets = targets.squeeze().long()
                outputs = outputs.softmax(dim=-1)
                targets = targets.float().resize_(len(targets), 1)

            y_true = torch.cat((y_true, targets), 0)
            y_score = torch.cat((y_score, outputs), 0)

        y_true = y_true.numpy()
        y_score = y_score.detach().numpy()

        evaluator = Evaluator(datasource.data_flag, split)
        metrics = evaluator.evaluate(y_score)

        #print('%s  auc: %.3f  acc:%.3f' % (split, *metrics))
        print('%s  auc: %.3f  acc:%.3f' % (split, metrics[0], metrics[1]))

def server_aggregate(global_model, client_models,client_lens):
    global_dict = global_model.state_dict()
    for k in global_dict.keys():
        global_dict[k] = torch.stack([client_models[i].state_dict()[k].float() for i in range(len(client_models))], 0).mean(0)
    global_model.load_state_dict(global_dict)

def server_aggregate_weights(global_model, client_weights,client_lens):
    global_dict = global_model.state_dict()
    for k in global_dict.keys():
        global_dict[k] = torch.stack([client_weights[i][k].float() for i in range(len(client_weights))], 0).mean(0)
    global_model.load_state_dict(global_dict)


print('==> worker trained model ...')
print(list(mymodel.parameters())[-1])

print('==> worker Saving model ...')
dic = mymodel.state_dict()
torch.save(dic, 'saved.model')

with open("saved.model", "rb") as fd:
    buf = io.BytesIO(fd.read())

# send over


#print('==> empty global model ...')
#model3 = model.Net(in_channels=datasource.n_channels, num_classes=datasource.n_classes)
#print(list(model3.parameters())[-1])
#client_models = [model3]

#print('==> load received client model ...')
#model2 = model.Net(in_channels=datasource.n_channels, num_classes=datasource.n_classes)
#model2.load_state_dict(torch.load(buf))
#print(list(model2.parameters())[-1])
#client_models.append(model2)

#server_aggregate(model3,client_models,len(client_models))
#print('==> aggregation...')
#print(list(model3.parameters())[-1])

print('==> empty global model ...')
model3 = model.Net(in_channels=datasource.n_channels, num_classes=datasource.n_classes)
print(list(model3.parameters())[-1])
client_weights = [model3.state_dict()]
client_weights.append(torch.load(buf))

server_aggregate_weights(model3,client_weights,len(client_weights))
print('==> aggregation...')
print(list(model3.parameters())[-1])


#print('==> Train ...')
train()

#print('==> Evaluating ...')
test('train')
test('test')
