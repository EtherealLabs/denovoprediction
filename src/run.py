def main():
	sequence = input("Enter a sequence")
	pipeline = LinearPipeline(sequence)
	pipeline.generateDeNovoPrediction()

if __name__ == '__main__':
	main()