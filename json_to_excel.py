import os
import json
from enum import Enum, unique
from debug import DebugMessage, DebugExit


class JTEData():
    work_book = None
    work_sheet = None
    dlg_json = {}
    flow_order = []


@unique
class XlHead(Enum):
    '''Excel表格的表头枚举'''
    GUID = 1
    TechIndex = 2
    TechJump = 3
    WorkIndex = 4
    Owner = 5
    Content = 6
    WorkJump = 7


@unique
class DlgNodeType(Enum):
    '''DlgSystem中的节点类型
    Start: -1, Sequence: 0, Speech: 1, Selector: 2, End: 3.
    '''
    Start = -1
    Sequence = 0
    Speech = 1
    Selector = 2
    End = 3


class JsonToExcel(object):
    def __init__(self):
        super(JsonToExcel, self).__init__()
        print("JsonToExcel Init.")
        # get json file path
        json_dir = os.path.abspath(os.path.join(os.getcwd(), "../.."))
        json_path = '%s/Dialogue/Dlg_TestFile.dlg.json' % json_dir
        # factory
        self.dlg_json_loader(json_path)

    @staticmethod
    def dlg_json_loader(json_file):
        """加载DlgSystem资产的json文件
        """
        if not os.path.exists(json_file):
            DebugExit("Dlg json's path")
            return

        with open(json_file, encoding="UTF-8") as f:
            dj_file = json.load(f)
        if not dj_file:
            return

        # 获取开始节点
        JTEData.dlg_json = dj_file
        print("Dlg json has been loaded.")
        f.close()

    @staticmethod
    def get_node_children():
        '''获取所有node中index与children的关系
        （StartNode的索引记作-1）
        '''
        dlgfile = JTEData.dlg_json
        if not dlgfile:
            DebugExit("Dlg json")
            return

        node_relations = {}
        start_children = dlgfile["StartNode"]["Children"]
        start_targets = []
        # StartNode
        for child in start_children:
            start_targets.append(child["TargetIndex"])
        node_relations[-1] = start_targets
        # Other nodes
        all_nodes = dlgfile["Nodes"]
        for node in all_nodes:
            node_index = node["__index__"]
            node_targets = []
            node_children = node["Children"]
            for child in node_children:
                node_targets.append(child["TargetIndex"])
            node_relations[node_index] = node_targets

        # DebugMessage("Node Realations", node_relations)

        return node_relations

    @staticmethod
    def flow_order(node_and_children):
        """将node按flow的先后顺序排序。
        依赖于node_relations。
        """
        if not node_and_children:
            DebugExit("Node and children")
            return

        flow_dict = {}
        flow_order = [-1]

        # 先处理StartNode
        start_node = node_and_children.pop(-1)
        flow_dict[-1] = start_node

        rec = -1
        while node_and_children != {}:
            # 拿到flow中最后一个有效的chidren的第一个child
            flow_revers = list(flow_dict.values())
            flow_revers.reverse()
            for target_list in flow_revers:
                if target_list == []:
                    continue
                last_node_first_child = target_list.pop(0)
                break
            DebugMessage("当前处理节点", last_node_first_child)

            # 一些安全措施
            if last_node_first_child == rec:
                DebugMessage("发现重复处理", rec)
                break
            rec = last_node_first_child

            # 检查child是否也是其他节点的child
            same_elm_found = False
            for node_children in node_and_children.values():
                if last_node_first_child in node_children:
                    same_elm_found = True
                    DebugMessage("发现该节点出现在后续流程中", last_node_first_child)
                    break

            # TODO 如果节点有多个入链
            # 需要判断其是否处于一个循环链中，
            # 如果是的话，先加入flow当中
            DebugMessage("Current Flow", flow_dict)
            if same_elm_found:
                JsonToExcel.is_loop_flow(
                    last_node_first_child, node_and_children)

            # 如果其他节点没有该child，则将其置入flow
            if not same_elm_found:
                popitem = node_and_children.pop(last_node_first_child)
                flow_dict[last_node_first_child] = popitem
                flow_order.append(last_node_first_child)

        DebugMessage("Flow Order", flow_order)

        return flow_order

    @staticmethod
    def is_loop_flow(index, node_and_children):
        """判断一个node是否处于循环当中。
        好几把烦啊我要哭了"""

        parse_record = {}

        parse_record[index] = node_and_children[index]

        # print(parse_record)

        r_prec = list(parse_record.values())
        r_prec.reverse()

        for targets in r_prec:
            if targets == []:
                continue
            last_node = targets[0]

    @staticmethod
    def indent_level(node_and_children: dict, flow_order: list):
        """计算每个节点的缩进等级。
        依赖于node_relations，以及flow_order。
        """
        if not node_and_children:
            DebugExit("Node Relations")
            return

        if not flow_order:
            DebugExit("Flow Order")
            return

        indent_level = {}

        for index in flow_order:

            branch_flag = False  # 分支标记
            in_links = []  # 所有入链的来源节点

            # 检查index在children中出现的次数
            t = 0
            for n_key, n_value in node_and_children.items():
                if index in n_value:
                    t += 1  # 出现次数
                    in_links.append(n_key)  # 记录入链
                    if n_value.__len__() >= 2:
                        branch_flag = True  # 判断是分支
            # 检查完毕

            # 如果一个index在所有出链中出现次数为0，
            # 该index有可能对应着一个开始节点或者悬浮节点，
            # 将其等级设置为0即可。
            if t == 0:
                indent_level[index] = 0
            # 如果一个index在所有出链中次数为1，
            # 检查其入链的来源节点是否为分支，
            # 如果是分支，则设置其缩进等级+1，否则继承缩进等级。
            elif t == 1:
                in_link = in_links[0]
                level = indent_level[in_link]
                if branch_flag:
                    level += 1
                indent_level[index] = level
            # 如果一个index在所有出链中次数大于等于2，
            # 获取所有入链的来源节点的缩进等级，进而找到最小值，
            # 使缩进等级等于最小值-1（需保证大于0）
            elif t >= 2:
                link_levels = []
                for link in in_links:
                    link_level = indent_level[link]
                    link_levels.append(link_level)
                level = min(link_levels)
                if level >= 1:
                    level -= 1

                indent_level[index] = level

        DebugMessage("Indent Level", indent_level)

        return indent_level


if __name__ == "__main__":
    JsonToExcel()
    # TempTest
    node_and_children = JsonToExcel.get_node_children
    flow_order = JsonToExcel.flow_order(node_and_children())
    # JsonToExcel.indent_level(node_and_children(), flow_order)
