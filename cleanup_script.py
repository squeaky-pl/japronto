import sys

def main():
    fp = open(sys.argv[1])

    for line in fp:
        line = line.rstrip()
        if line.startswith('\t'):
            rest = line[18:]
            name_addr, _, rest = rest.partition(' ')
            name, _, addr = name_addr.partition('+')
            line = line[:18] + name + ' ' + rest

        print(line)

    fp.close()

if __name__ == '__main__':
    main()
